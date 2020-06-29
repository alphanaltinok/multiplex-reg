# FROM python:3
FROM continuumio/anaconda3

# set a directory for the app
WORKDIR /usr/src/app

# Create the environment:
COPY environment.yml .
RUN conda env create -f environment.yml

# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# copy all the files to the container
COPY . .

# run the command
# CMD ["python", "./reg_multiplex.py"]
# ENTRYPOINT ["conda", "run", "-n", "reg", "python", "/usr/src/app/reg_multiplex.py", "/usr/src/data/input/", "/usr/src/data/output/"]
ENTRYPOINT ["conda", "run", "-n", "reg", "python", "/usr/src/app/reg_multiplex.py"]
