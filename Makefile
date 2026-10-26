PYTHON = python
MANAGE = $(PYTHON) manage.py

install: #install dependencies
	pip install -r requirements.txt

freeze: 
	pip freeze > requirements.txt

migrations: #create new database migrations
	$(MANAGE) makemigrations

migrate: #apply database migrations
	$(MANAGE) migrate

run: #run the django development server
	$(MANAGE) runserver

user: #create a superuser
	$(MANAGE) createsuperuser

test: #run the test suite
	$(MANAGE) test
