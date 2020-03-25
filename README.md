# PyDGN

## [Wiki](https://github.com/diningphil/PyDGN/wiki)

## Description
![](https://github.com/diningphil/PyDGN/blob/master/images/pydgn-logo.png)
This is a Python library to easily experiment with [Deep Graph Networks](https://arxiv.org/abs/1912.12693) (DGNs). It provides automatic management of data splitting, loading and the most common experimental settings. It also handles both model selection and risk assessment procedures, by trying many different configurations in parallel (CPU).
This repository is built upon the [Pytorch Geometric Library](https://pytorch-geometric.readthedocs.io/en/latest/), which provides support for data management.

If you happen to use or modify this code, please remember to cite our tutorial paper:

[Bacciu Davide, Errica Federico, Micheli Alessio, Podda Marco: *A Gentle Introduction to Deep Learning for Graphs*](https://arxiv.org/abs/1912.12693). *Under Review*

If you are interested in a rigorous evaluation of Deep Graph Networks, check this out:

[Errica Federico, Podda Marco, Bacciu Davide, Micheli Alessio: *A Fair Comparison of Graph Neural Networks for Graph Classification*](https://openreview.net/pdf?id=HygDF6NFPB). *Proceedings of the 8th International Conference on Learning Representations (ICLR 2020).* [Code](https://github.com/diningphil/gnn-comparison)

*Missing features*
- Support to multiprocessing in GPU is not provided yet, but single GPU support is enabled.

## Installation:
(We assume **git** and **Miniconda/Anaconda** are installed)

#### PyTorch (CPU version) 

    source setup/install_cpu.sh

#### PyTorch (CUDA version 10.1) 

    source setup/install_cuda.sh
     
Remember that [PyTorch MacOS Binaries dont support CUDA, install from source if CUDA is needed](https://pytorch.org/get-started/locally/)

## Usage:

### Preprocess your dataset (see also Wiki)
    python PrepareDatasets.py --config-file [your config file]

### Launch an experiment in debug mode (see also Wiki)
    python LaunchExperiments.py --config-file [your config file] --data-root [root folder of your data] --dataset-name [name of the dataset] --dataset-class [class that handles the dataset] --final-training-runs [how many final runs when evaluating on test. Results are averaged] --debug

## Credits:
This is a joint project with **Marco Podda** ([Github](https://github.com/marcopodda)/[Homepage](https://sites.google.com/view/marcopodda/home)), whom I thank for his relentless dedication.

## Contributing
**This research software is provided as-is**. We are working on this library in our spare time. 

If you find a bug, please open an issue to report it, and we will do our best to solve it. For generic/technical questions, please email us rather than opening an issue.

## License:
PyDGN is GPL 3.0 licensed, as found in the LICENSE file.