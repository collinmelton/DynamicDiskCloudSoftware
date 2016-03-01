# DynamicDiskCloudSoftware
This software is designed to run genomics workflows on the Google Compute Engine. The distinguishing characteristic of this software is that it is designed to automatically mount and unmount disk storage as needed during the course of the workflow. This is in contrast to NFS storage or saving intermediate results to cloud storage. In certain use cases this strategy more closely approaches optimal resource utilization.

# Contents
- [Get Setup with GCE](#get-setup-with-gce)
- [Configure GCE Image](#configure-gce-image)
- [Get Service Account Authentication Info](#get-service-account-authentication-info) 
- [Run Test](#run-test) 
- [Web Server Version](#web-server-version)

# Get Setup with GCE
Get a GCE Account and setup a Google Cloud Storage bucket. URI should look something like this gs://bucketname/

# Configure GCE Image
In this section we will configure a GCE Image for use as the OS on both the Master and Worker instances. 

## Boot GCE Instance
From the GCE developers console boot a new instance. I've chosen CENTOS6.6 as the base image, but if you use a different base you may need to modify the software installation below. Make sure to enable full access to storage during setup. This is important because you will save you image to your Google Cloud Storage bucket. 

## Install Software (for CENTOS6.6)
1. SSH into the new instance. 

2. Install Git

	sudo yum install git
	
3. Clone this project and note project location

	git clone git@github.com:collinmelton/DynamicDiskCloudSoftware.git
	
4. Install project specific dependencies

	** install development tools **
	
	sudo yum install libevent-devel python-devel
	
	sudo yum groupinstall "Development tools"
	
	** install pip, apache-libcloud, PyCrypto, and httplib2 **
	
	curl -o get-pip.py https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py
	
	sudo python get-pip.py
	 
	sudo pip install apache-libcloud
	
	sudo pip install PyCrypto
	
	sudo pip install httplib2
	
	** a bunch of crap to install python2.7, easyinstall, pip, and get PyCrypto etc **
	
	sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm
	 
	wget http://www.python.org/ftp/python/2.7.6/Python-2.7.6.tgz
	
	tar xvzf Python-2.7.6.tgz
	
	sudo yum install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel
	
	cd Python-2.7.6
	
	sudo ./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
	
	sudo make && sudo make altinstall
	
	wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
	
	sudo /usr/local/bin/python2.7 ez_setup.py
	
	sudo /usr/local/bin/easy_install-2.7 pip
	
	sudo /usr/local/bin/pip2.7 install apache-libcloud
	
	sudo /usr/local/bin/pip2.7 install PyCrypto
	
	sudo /usr/local/bin/pip2.7 install httplib2

	sudo /usr/local/bin/pip2.7 install psutil

	sudo /usr/local/bin/pip2.7 install -U https://github.com/google/google-visualization-python/zipball/master

## Configure SSH Keys

	ssh-keygen -t rsa -b 4096 -C "yourname@yourdomain.com"
	
	eval "$(ssh-agent -s)"
	
	ssh-add ~/.ssh/id_rsa

	edit ~/.ssh/authorized keys by adding the key located in ~/.ssh/id_rsa.pub, in this setup the master running this image will have the same public key as the worker and we want the master to be able to ssh into the worker so we need to add the master's public key to the list of authorized keys 

## Authorize the instance with gcloud auth login

	** I also did an auth login so I could copy to my cloud storage bucket in next step, I didn't expect to need to do this as the instance should have been authorized to access cloud storage during creation, it might have to do with our project configuration settings or my misunderstanding of how things work
	
	gcloud auth login

## Create Image and Save to Cloud Storage

	sudo gcimagebundle -d /dev/sda -o /tmp/ --log_file=/tmp/abc.log
	
	** check to see name of the image file from output of above command and edit commands below with this name **
	
	gsutil cp /tmp/imagename.image.tar.gz gs://yourbucketname/
	
	** below you can name your image, I've name the image cloudtest2, I think this can also be done with gcloud ** 
	
	~/google-cloud-sdk/bin/gcutil --project "your_project_name" addimage cloudtest2 gs://yourbucketname/imagename.image.tar.gz
	or 
	gcloud compute images create cloudtest2 --source-uri gs://yourbucketname/imagename.image.tar.gz


# Get Service Account Authentication Info
In order to run the software you need to get a service account email address and a pem file. See instructions here: https://cloud.google.com/storage/docs/authentication#service_accounts

You should make a pem file and note your service account email address in the format: numbersandletters@developer.gserviceaccount.com


# Run Test

	** Use the GCE Instance used to create the image above or make a new instance with access to compute and storage authorized with the image you created above. **
	** Navigate to the directory for this project then go to the Master folder. **
	python2.7 RunJobs.py --I test_instances.csv --D test_disks.csv --P yourprojectname --PM test.pem --E somelettersandnumbers@developer.gserviceaccount.com --RD /home/yourusername/ --SD ./
	
# Web Server Version
I am developing an updated version of the software that runs a webserver (link coming soon). This version allows the user to generate a workflow, launch a workflow, and view progress and performance of the workflow as it runs.
	
