#!/usr/bin/env python
"""mini cnn benchmarks in pytorch to identify regression issues"""

import logging
import os
import platform
import subprocess
import time
from collections import namedtuple

import psutil
import torch
import torch.nn as nn
import torchvision.models as models
import torch.optim as optim

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


logging.info("Platform details")
logging.info("=" * 71)
if platform.system() == "Linux":
    logging.info(
        "cpu name :: %s"
        % str(
            subprocess.check_output(
                "cat /proc/cpuinfo | grep 'model name' | head -n 1", shell=True
            )
        ).split(":")[1][:-3]
    )
    logging.info("operating system :: %s" % platform.platform())
    logging.info("=" * 71)
    logging.info("Pytorch config")
    logging.info("=" * 71)
    logging.info("pytorch version :: %s" % torch.__version__)
    logging.info("mkl available :: %s" % "Yes" if torch.has_lapack else "No")
    logging.info("lapack available :: %s" % "Yes" if torch.has_mkl else "No")
    mkldnn = os.path.isfile(
        os.path.join(torch.get_file_path(), "torch", "lib", "libmkldnn.so")
    )
    logging.info("mkldnn available :: %s" % "Yes" if mkldnn else "No")
    logging.info("=" * 71)
else:
    logging.info("Exiting... not a linux system")
    exit(1)


class BenchMarks:
    """set of convnet benchmarks"""

    Model = namedtuple("Model", "name model batch")
    alexnet = Model(name="alexnet", model=models.alexnet, batch=(64, 224, 224))
    resnet18 = Model(name="resnet18", model=models.resnet18, batch=(128, 224, 224))
    resnet50 = Model(name="resnet50", model=models.resnet50, batch=(256, 224, 224))
    vgg16 = Model(name="vgg16", model=models.vgg16, batch=(256, 224, 224))
    squeezenet = Model(
        name="squeezenet", model=models.squeezenet1_1, batch=(256, 224, 224)
    )

    def select(self, model_name=None):
        """select models to be run"""

        logging.info("Run details")
        logging.info("=" * 71)
        models = [
            self.alexnet,
            self.resnet18,
            self.resnet50,
            self.vgg16,
            self.squeezenet,
        ]
        if model_name:
            self.models = [
                model for model in models for name in model_name if name == model.name
            ]
        logging.info("Selected model(s) :: ")
        for m in self.models:
            logging.info("%s ------------- Batchsize :: %s " % (m.name, m.batch))
        logging.info("=" * 71)

    @staticmethod
    def synth_data(batch):
        channel = 3
        batch_size = batch[0]
        height = batch[1]
        weight = batch[2]
        inp_data = torch.rand(batch_size, channel, height, weight)
        label = torch.arange(1, batch_size + 1).long()
        return inp_data, label

    def main(self, models):
        self.select(models)
        for m in self.models:
            logging.info("=" * 71)
            logging.info("Running an instance of :: %s" % m.name)
            self.run(m)

    def run(self, model_tuple):
        t_forward, t_backward, t_update = 0, 0, 0
        steps = 10
        model, batch = model_tuple.model(), model_tuple.batch
        learning_rate = 0.01
        input_data, label = BenchMarks.synth_data(batch)
        optimizer = optim.SGD(model.parameters(), lr=learning_rate)
        loss_fn = nn.CrossEntropyLoss()
        model.eval()
        optimizer.zero_grad()
        logging.info("Number of iterations :: %d" % steps)
        logging.info("Learning rate:: %f" % learning_rate)
        for _ in range(steps):
            t_1 = time.time()
            output = model(input_data)
            t_2 = time.time()
            loss = loss_fn(output, label)
            loss.backward()
            t_3 = time.time()
            optimizer.step()
            t_4 = time.time()
            t_forward += t_2 - t_1
            t_backward += t_3 - t_2
            t_update += t_4 - t_2
        forward_avg = t_forward / steps
        backward_avg = t_backward / steps
        update_avg = t_update / steps
        total_time = forward_avg + backward_avg + update_avg
        logging.info(
            "Avg time taken for training %s :: %f" % (model_tuple.name, total_time)
        )
        logging.info("Avg inference time:: %f" % forward_avg)
        logging.info(
            "Training throughput :: %f images/sec" % (model_tuple.batch[0] / total_time)
        )
        logging.info(
            "Inference throughput :: %f images/sec"
            % (model_tuple.batch[0] / forward_avg)
        )
        logging.info("=" * 71)


if __name__ == "__main__":
    bmarks = BenchMarks()
    bmarks.main(models=["alexnet", "resnet18", "resnet50"])