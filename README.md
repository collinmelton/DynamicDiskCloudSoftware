# DynamicDiskCloudSoftware
This software is designed to run genomics workflows on the Google Compute Engine. The distinguishing characteristic of this software is that it is designed to automatically mount and unmount disk storage as needed during the course of the workflow. This is in contrast to NFS storage or saving intermediate results to cloud storage. In certain use cases this strategy more closely approaches optimal resource utilization.

# Contents
- [Get Setup with GCE](#get-setup-with-gce)
- [Configure GCE Image](#configure-gce-image)
- [Get Service Account Authentication Info](#get-service-account-authentication-info) 
- [Run Test](#run-test) 

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
	
## Create Image and Save to Cloud Storage

	sudo gcimagebundle -d /dev/sda -o /tmp/ --log_file=/tmp/abc.log
	
	** check to see name of the image file from output of above command and edit commands below with this name **
	
	gsutil cp /tmp/imagename.image.tar.gz gs://yourbucketname/
	
	** below you can name your image, I've name the image cloudtest **
	
	~/google-cloud-sdk/bin/gcutil --project "your_project_name" addimage cloudtest gs://yourbucketname/imagename.image.tar.gz


## Configure SSH Keys

	ssh-keygen -t rsa -b 4096 -C "yourname@yourdomain.com"
	
	eval "$(ssh-agent -s)"
	
	ssh-add ~/.ssh/id_rsa

# Get Service Account Authentication Info
In order to run the software you need to get a service account email address and a pem file. See instructions here: https://cloud.google.com/storage/docs/authentication#service_accounts

You should make a pem file and note your service account email address in the format: numbersandletters@developer.gserviceaccount.com


# Run Test
