import logging

import torch
from torch import nn
import numpy as np
import torch.nn.functional as F

from nnpde.functions import helpers
import nnpde.functions.iterative_methods as im
from nnpde import metrics

__author__ = "Francesco Bardi, ADDyourName"
__credits__ = ["Francesco Bardi",
               "ADDyourName"]
__license__ = "GPL"
__maintainer__ = "Francesco Bardi"
__status__ = "Development"


class JacobyWithConv:
    """A class to obtain the optimal weights"""

    def __init__(self,
                 net=None,
                 batch_size=1,
                 learning_rate=1e-6,
                 max_iters=1000,
                 nb_layers=3,
                 tol=1e-6,
                 k_range=[1, 20],
                 N=16):

        if net is None:
            self.net = nn.Sequential(
                *[nn.Conv2d(1, 1, 3, padding=1, bias=False) for _ in range(nb_layers)])
        else:
            self.net = net

        # Set the optimizer, you have to play with lr: if too big nan
        self.learning_rate = learning_rate
        self.optim = torch.optim.SGD(self.net.parameters(), lr=learning_rate)
        ##optim = torch.optim.Adadelta(net.parameters())
        #optim = torch.optim.Adam(net.parameters(), lr=1e-6)
        #optim = torch.optim.ASGD(net.parameters())

        self.batch_size = batch_size
        self.max_iters = max_iters
        self.tol = tol
        self.k_range = k_range

        self.T = helpers.get_T(N)
        self.H = None
        self.N = N

    def _optimization_step_(self):
        self.net.zero_grad()

        # Randomly sample a subset of problem_instances
        problem_idx = np.random.choice(
            np.arange(len(self.problem_instances)), self.batch_size, replace=0)
        problem_instances_batch = [
            self.problem_instances[i] for i in problem_idx]

        # Compute loss using only batch
        loss = metrics.compute_loss(self.net, problem_instances_batch)

        # Backpropagate loss function
        loss.backward(retain_graph=True)

        # Update weights
        self.optim.step()

    def fit(self, problem_instances):
        """  
             Returns
             -------
             self : object
                 Returns an instance of self.
        """
        # Initialization
        self.problem_instances = problem_instances
        losses = []
        prev_total_loss = metrics.compute_loss(self.net,
                                               self.problem_instances).item()

        # Optimization loop
        for n_iter in range(self.max_iters):

            # Update weights
            self._optimization_step_()

            # Compute total loss
            total_loss = metrics.compute_loss(self.net,
                                              self.problem_instances)

            # Check convergence
            if total_loss.item() <= self.tol or np.abs(total_loss.item() - prev_total_loss) < self.tol:
                losses.append(total_loss.item())
                self.losses = losses
                return self

            # Store lossses for visualization
            losses.append(total_loss.item())
            prev_total_loss = total_loss.item()

            # Display information every 100 iterations
            if n_iter % 100 == 0:
                logging.info(
                    f"iter {n_iter} with total loss {prev_total_loss}")

        #self.H = helpers.conv_net_to_matrix(self.net, self.N)
        self.losses = losses

        return self
