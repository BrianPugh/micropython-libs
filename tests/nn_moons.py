import random

import matplotlib.pyplot as plt
import numpy as np
import pytest
from nn import MLP, Layer, Neuron, Value
from sklearn.datasets import make_moons


@pytest.mark.slow
def test_moons():
    np.random.seed(1337)
    random.seed(1337)

    X, Y = make_moons(n_samples=100, noise=0.1)
    Y = Y * 2 - 1  # make y be -1 or 1
    # X - (n_samples, 2)
    # Y - (n_samples,) in set {-1, 1}
    n_exemplars = len(Y)

    # initialize a model
    model = MLP(2, [16, 16, 1])  # 2-layer neural network
    print(model)
    print("number of parameters", len(model.parameters()))

    X = [[Value(z) for z in x] for x in X]
    # optimization loop
    for k in range(100):
        # forward pass
        preds = [model(x) for x in X]

        # svm "max-margin" loss
        data_loss = sum((1 + -y * pred).relu() for pred, y in zip(preds, Y))
        data_loss /= n_exemplars

        # L2 regularization
        alpha = 1e-4
        reg_loss = alpha * sum(p * p for p in model.parameters())
        total_loss = data_loss + reg_loss

        accuracy = sum((y > 0) == (pred.data > 0) for pred, y in zip(preds, Y))
        accuracy /= n_exemplars

        # backward
        model.zero_grad()
        total_loss.backward()
        # update (sgd)
        learning_rate = 1.0 - 0.9 * k / 100
        for p in model.parameters():
            p.data -= learning_rate * p.grad
        if k % 1 == 0:
            print(f"step {k} loss {total_loss.data}, accuracy {accuracy:.2%}")
