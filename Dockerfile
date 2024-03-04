FROM python:3.11.5
ENV PYTHONUNBUFFERED 1
COPY requirements.txt /workdir/

RUN apt-get update
RUN apt-get install sudo -y build-essential \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx
RUN pip install --no-cache-dir -r /workdir/requirements.txt
RUN apt-get clean
COPY ./ /workdir/

WORKDIR /workdir

CMD ["EXPOSE", "9666"]
# Run the application
CMD ["python3", "main.py"]
