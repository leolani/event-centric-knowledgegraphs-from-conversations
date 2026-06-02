# Event-centricKnowledge Graph tutorial

## Description

This repository contains a Jupyter notebook ```event-centric-capsules.ipynb``` that showcases how to turn a dialogue about eventys into an event-centric RDF graph.

## Getting started

### Prerequisites

1. This repository uses Python >= 3.11 . Be sure to run in a virtual python environment (e.g. conda, venv, mkvirtualenv,
   etc.). For example:

   ```bash
   conda create --name event-kg python=3.11
   conda activate event-kg
   ```

2. You need to download and run [GraphDB Free](http://graphdb.ontotext.com/). Please create a repository
   called `event_sandbox`.

### Installation

1. In the root directory of this repo run

    ```bash
    pip install -r requirements.txt
    python -m ipykernel install --name=event-kg
    ```

### Usage

You may run any of the notebooks by launching the Jupyter Notebook interface:

   ```bash
   jupyter notebook 
   ```

## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any
contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License.
See [`LICENSE`](https://github.com/leolani/event-centric-knowledgegraphs-from-conversations/blob/main/LICENSE) for more information.

## Authors

* [Piek Vosse](https://piekvossen.github.io/)