import torch
import torch.nn.functional as F
from pytorch_metric_learning.distances import CosineSimilarity

from ..utils import common_functions as c_f
from .diversity_loss import DiversityLoss
from .entropy_loss import EntropyLoss


def get_probs(mat, mask, y, dist_is_inverted):
    if not dist_is_inverted:
        mat *= -1
    mat = F.softmax(mat, dim=1)
    n, m = mat.shape
    y = y.repeat(n, 1)[mask].view(n, m)

    target_probs = torch.sum(mat * y, dim=1, keepdims=True)
    src_probs = torch.sum(mat * (1 - y), dim=1, keepdims=True)
    return torch.cat([src_probs, target_probs], dim=1)


def get_loss(probs, ent_fn, div_fn, with_ent, with_div):
    loss = 0
    if with_ent:
        loss += -ent_fn(probs)
    if with_div:
        loss += -div_fn(probs)
    return loss


class ISTLoss(torch.nn.Module):
    """
    Implementation of the I_st loss from
    [Information-Theoretical Learning of Discriminative Clusters for Unsupervised Domain Adaptation](https://icml.cc/2012/papers/566.pdf)
    """

    def __init__(self, distance=None, with_ent=True, with_div=True):
        super().__init__()
        self.distance = c_f.default(distance, CosineSimilarity, {})
        if not (with_ent or with_div):
            raise ValueError("At least one of with_ent or with_div must be True")
        self.with_ent = with_ent
        self.with_div = with_div
        self.ent_loss_fn = EntropyLoss(after_softmax=True)
        self.div_loss_fn = DiversityLoss(after_softmax=True)

    def forward(self, x, y):
        """
        Arguments:
            x: source and target features
            y: domain labels, i.e. 0 for source domain, 1 for target domain
        """
        n = x.shape[0]
        if torch.min(y) < 0 or torch.max(y) > 1:
            raise ValueError("y must be in the range 0 and 1")
        if y.shape != torch.Size([n]):
            raise TypeError("y must have shape (N,)")

        mat = self.distance(x)
        # remove self comparisons
        mask = ~torch.eye(n, dtype=torch.bool)
        mat = mat[mask].view(n, n - 1)
        probs = get_probs(mat, mask, y, self.distance.is_inverted)

        return get_loss(
            probs, self.ent_loss_fn, self.div_loss_fn, self.with_ent, self.with_div
        )

    def extra_repr(self):
        """"""
        return c_f.extra_repr(self, ["with_div"])
