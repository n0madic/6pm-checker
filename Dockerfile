FROM python:3-alpine

WORKDIR /app

ADD requirements.txt /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt && \
    rm -rf ~/.cache

ADD *.py /app

CMD ["python", "6pm-checker.py"]