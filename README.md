<div align="center">

![Python](https://img.shields.io/badge/python-3.11-4584b6?labelColor=ffde57&logo=python) ![Django](https://img.shields.io/badge/django-4.2-white?labelColor=092e20&logo=django)
![PostgreSQL](https://img.shields.io/badge/postgresql-14.6-4169E1?labelColor=white&logo=PostgreSQL) ![Redis](https://img.shields.io/badge/redis-4.6.0-A41E11?labelColor=white&logo=Redis) ![Celery](https://img.shields.io/badge/celery-5.3.1-green?labelColor=grey&logo=Celery)
![Black](https://img.shields.io/badge/code%20style-black%23.7.0-black?labelColor=white)

</div>

# Django starter project

Use this project to start off on a Django backend with REST framework. The docker compose setup will start a PostgreSQL instance with Postgis enabled and the settings are connected to this database by default.

### Usage

Clone the starter project to your device:

`git clone https://github.com/Mobiux-Labs/starter-project-django.git`

- Build docker containers. This is a one time process only.
  `docker-compose up --build`
  This command may require elevation to `sudo`.

- For all future instances you can just
  `docker-compose up`
  This command may require elevation.

- To enter the server shell:
  `docker-compose exec server /bin/bash`
  This command may require elevation.

- Set up localsettings.py file in `apiserver/apiserver`:
  `touch apiserver/localsettings.py`
  You need to then import localsettings at the end of apiserver/settings.py file. `from .localsettings.py import *`
  This is already part of the .gitignore and ensures that data(secrets) stored in the localsettings are not exposed to the git repository.

- **Project secret key setup** This step is a must for every project.
  (In the server container shell)
  `python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
  Store this 50character string in variable `SECRET_KEY` in localsettings.py.

- Install python Black formatter in your editor.
  Follow the instructions based on the editor you are comfortable using.

- Setup your project virtual environment using `python -m venv venv` in the root
  directory. Read more about venv and how to activate it
  [here](https://docs.python.org/3/library/venv.html). Install all python
  packages used in the project from the requirements folder using the command
  `pip install -r /apiserver/requirements/dev.txt`

- Check your version of pre-commit with `pre-commit --version`. You still need
  to activate the pre-commit hooks using `pre-commit install`.

- Alter the /sonar-project.properties file with a new token and project id.
  Set up a few basic branches like dev. Sonarqube workflow will run on this branch.

## Congratulations, You have now set up your starter project 👍

Work pending:

- Admin interface setup for users and groups.
- Configure REST framework with token and session auth.
- Create custom user model.
- Security related configuration in the settings file.
- Storage setup with ~~S3~~ and Cloudfront (optional)
- ~~Enable Django filters.~~
- ~~Enable Redis cache.~~
- ~~Enable Celery with Redis as broker.~~
- ~~Mail setup.~~
