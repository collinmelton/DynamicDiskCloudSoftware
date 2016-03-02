# DynamicDiskCloudSoftware
This software is designed to run genomics workflows on the Google Compute Engine. The distinguishing characteristic of this software is that it is designed to automatically mount and unmount disk storage as needed during the course of the workflow. This is in contrast to NFS storage or saving intermediate results to cloud storage. In certain use cases this strategy more closely approaches optimal resource utilization.

# Contents
- [Get Setup with GCE](#get-setup-with-gce)
- [Configure GCE Image](#configure-gce-image)
- [Get Service Account Authentication Info](#get-service-account-authentication-info) 
- [Constructing Disk and Instance CSV Files](#constructing-disk-and-instance-csv-files)
- [Run Test](#run-test) 
- [Web Server Version](#web-server-version)
- [Alternative Licensing](#alternative-licensing)

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

# Constructing Disk and Instance CSV Files
The workflow is specified by the disk and instance files. There is no internal check for validity of your specified workflow so be careful to map it out and not make errors! Make sure names of instances and disks comply with GCE standards (Name must start with a lowercase letter followed by up to 62 lowercase letters, numbers, or hyphens, and cannot end with a hyphen).

## Disk File
The disk file contains information including disk names, types, and sizes. A description of columns to include in this file are as follows:

|Column Name | Description|
|--- | ---|
|notes | Any notes you want to include about this row.|
|name | The name of the disk. $JOBID and $JOBMULT variables in the name will be replaced with job id and job multiplicity |variables at run time.|
|size | The size of the disk in GB.|
|location | Disk zone. Default is us-central-1a.|
|snapshot | Disk snapshot to use. Default is None|
|image | Disk image to use. Default is None|
|job_multiplicity | This is a string with variable names separated by the pipe &#124;.|
|job_id | The job id. Really this is just a scheme to replace the $JOBID variable in the name column with this value.|
|disk_type | The type of disk. Options are pd-standard or pd-ssd.|
|init_source| A location to copy to disk when initialized. This can be cloud storage bucket/folder combo or another disk mounted to the initial instance.|
|shutdown_dest | A location to save the disk contents to when the instance finishes. This can be cloud storage bucket/folder combo or another disk mounted to the instance.|

Note: To use default please write DEFAULT in place of specifying the column.

## Instance File
The instance file contains information including instance names, types, commands to run, instance dependencies, and disks to mount. A description of columns to include in this file are as follows:

|Column Name | Description|
|--- | ---|
|run | TRUE or FALSE whether to use or ignore this row.|
|notes | Any notes you want to include about this row.|
|name | The name of the instance. $JOBID and $JOBMULT variables in the name will be replaced with job id and job multiplicity |variables at run time.|
|dependencies | Names of instances that must complete before this instance is launched. Separate instance names by pipe &#124;.|
|read_disks| Names of disks separated by &#124; to mount in read mode.|
|read_write_disks| Names of disks separated by &#124; to mount in read/write mode.|
|boot_disk| Names of disk to use as a boot disk.|
|script| New line separated linux commands to run on instance|
|size| GCE instance specification (default is n1-standard-1).|
|image| The image to use. I believe this is only used if no boot disk is specified in the disk file and otherwise the image on the boot disk is used. Default is None.|
|location| The zone in which to boot the instance. (default is us-central1-a)|
|ex_network| A network to specify (I've never ended up using this so it could be buggy.) Default is 'default'.|
|ex_tags| Similar to ex_network this hasn't been tested but in theory should add tags to the instance.|
|ex_metadata| Similar to ex_network this hasn't been tested but in theory should add metadata to the instance.|
|job_multiplicity | This is a string with variable names separated by the pipe &#124;. Variables will be added with a leading dash to replace $JOBMULTNODASH and without a dash for $JOBMULTNODASH|
|var_multiplicity| This is an old option I haven't used in a while. I belive the idea was that you put in pipe separated variables and it replaces $VARMULT with these variables pasted together is some useful fashion. I don't really like this option and I'm thinking of deprecating it. I believe I initially used it to get variable names formatted for combining files.|
|job_id | The job id. Really this is just a scheme to replace the $JOBID variable in the name column with this value. The variable will be added in place of $JOBID with a trailing dash.|

# Run Test

	** Use the GCE Instance used to create the image above or make a new instance with access to compute and storage authorized with the image you created above. **
	** Navigate to the directory for this project then go to the Master folder. **
	python2.7 RunJobs.py --I test_instances.csv --D test_disks.csv --P yourprojectname --PM test.pem --E somelettersandnumbers@developer.gserviceaccount.com --RD /home/yourusername/ --SD ./
	
# Web Server Version
I am developing an updated version of the software that runs a webserver (https://github.com/collinmelton/DDCloudServer). This version allows the user to generate a workflow, launch a workflow, and view progress and performance of the workflow as it runs.

# Alternative Licensing
This project is licensed open source under GNU GPLv2. To inquire about alternative licensing options please contact the Stanford Office of Technology Licensing (www.otl.stanford.edu).
