import shutil
import unittest

import torch

from pytorch_adapt.datasets import DataloaderCreator
from pytorch_adapt.frameworks.ignite import Ignite
from pytorch_adapt.layers import DoNothingOptimizer
from pytorch_adapt.meta_validators import ReverseValidator
from pytorch_adapt.utils.savers import Saver
from pytorch_adapt.validators import AccuracyValidator

from .. import TEST_FOLDER
from ..adapters.get_dann import get_dann


def assert_perfect_forward(cls, forward_adapter, mv):
    for dataset_name in ["pseudo_train", "pseudo_val"]:
        dataset = getattr(mv, dataset_name)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=32)
        dataset_outputs = forward_adapter.get_all_outputs(dataloader, dataset_name)[
            dataset_name
        ]
        validator = AccuracyValidator()
        score = validator.score(epoch=0, src_val=dataset_outputs)
        cls.assertTrue(score == 1)


class TestReverseValidator(unittest.TestCase):
    def test_reverse_validator(self):
        for forward_with_validator in [True, False]:
            mv = ReverseValidator()
            forward_adapter, datasets = get_dann()
            reverse_adapter, _ = get_dann()
            pl_dataloader_creator = DataloaderCreator(
                all_val=True, val_kwargs={"batch_size": 32, "num_workers": 4}
            )
            dataloader_creator = DataloaderCreator(num_workers=1)
            forward_kwargs = {
                "datasets": datasets,
                "max_epochs": 3,
                "dataloader_creator": dataloader_creator,
            }
            reverse_kwargs = {
                "max_epochs": 3,
                "dataloader_creator": dataloader_creator,
                "validator": AccuracyValidator(),
            }
            if forward_with_validator:
                forward_kwargs["validator"] = AccuracyValidator()
                forward_kwargs["saver"] = Saver(folder=TEST_FOLDER)

            best_score, best_epoch = mv.run(
                forward_adapter,
                reverse_adapter,
                forward_kwargs,
                reverse_kwargs,
                pl_dataloader_creator=pl_dataloader_creator,
            )

            assert_perfect_forward(self, forward_adapter, mv)

            shutil.rmtree(TEST_FOLDER)
