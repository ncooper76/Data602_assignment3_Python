FROM python:3.6

RUN apt-get update && apt-get install && \
    apt-get install git
    
WORKDIR /home/ec2-user

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/ncooper76/Data602_assignment3_Python /home/ec2-user/apps
EXPOSE 5000
CMD ["python", "/home/ec2-user/apps/DATA602_assignement3.py"]
