# pull the official base image
FROM python:3.10.4-alpine
WORKDIR /usr/src/app
RUN pip install --upgrade pip 
COPY ./requirements.txt /usr/src/app
RUN python3 -m pip install -r requirements.txt --no-cache-dir
COPY . /usr/src/app
CMD ["python", "socketServer.py"]