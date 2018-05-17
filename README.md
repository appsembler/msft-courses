# Microsoft Courses Tools
Microsoft courses bulk import mini-tool for Open edX installations. This repo contains other scripts
for cleaning up incorrect imports and bulk deleting courses.

## Batch Course Imports
Upload the all courses files via `scp` ([Wondering how?](https://serverfault.com/a/264598/18125)) to the server.

Using a sudoer user, go to the working directory that has the courses `*.tar.gz` files:

```bash
$ tree
.
├── A subdirectory
│   ├── Implementing ETL with SQL Server Integration Services-DAT217x-2017_T4.tar.gz
...
├── Another subdirectory
│   ├── Introduction to Data Analysis using Excel-DAT205x-2017_T4.tar.gz
│   ├── Introduction to DevOps-DEV212x-2017_T4.tar.gz
│   ├── Introduction to DevOps Practices-DEVOPS200.1x-2017_T4.zip
...
│   ├── Introduction to ReactJS-DEV281x-2017_T4.tar.gz
│   ├── Introduction to R for Data Science-DAT204x-2017_T4.tar.gz
...
├── Windows Server 2016-Advanced Virtualization-INF219x-2017_T4.tar.gz
└── Writing Professional Code-DEV275x-2017_T4.zip

2 directories, 45 files
```

This tool supports arbitrary nesting of course files,
extracting `*.zip` files and installing libraries.

**Pro Tip:** 
 - Despite the above, it's better to import the courses into two batches a) one go for the `.tar.gz`. The way to 
   do this is by putting each group in a directory and `cd`'ing into that dir before running the script bellow.

### Course Files Naming Convention
It is a Microsoft convention to use name the courses like the following:
```
<COURSE_NAME>-<COURSE_CODE>-<COURSE-RUN>.tar.gz
```

So a course that looks like this:
```
Introduction to ReactJS-DEV281x-2017_T4.tar.gz
```

Will be imported by this tool as:

```
course-v1:Microsoft+DEV281x+2017_T4
```

**Pro Tip:** 
 - Some of the courses don't follow that convention. Please rename them: e.g. sometimes a course has a
   timestamp suffix: `Introduction to ReactJS-DEV281x-2017_T4-1519594558.tar.gz`. Please remove that `-1519594558` 
   suffix before the import.

### Executing the Import Script
The import script supports specifying both start and end date of the course and enrollment.
Those environment variables are optional, 
but once provided they'll be parsed into Python datetime strings, which will fail
if given incorrect values.

Run the following command:

```bash
$ START_DATE='2018-10-20' curl https://raw.githubusercontent.com/appsembler/msft-courses/master/import.sh | bash
```

Importing a single-course usually takes a minute, so the bulk importing 30 courses usually takes about half an hour.

**Pro Tip:** 
 - Sometimes the import breaks. Handle that in a divide and conquer process in which you'd try to import a
   smaller group of the courses until you find the offending one. Usually this boils down to the following errors: 
     * Incorrect library directory name: rename the directory inside the library `.tar.gz` file.
     * Other errors? Please document the error and the solution here.

## Removing Incorrect Imports
**Heads Up!**
 - This part is not tested very well. However, you're highly encouraged to test, use and improve to make it stable.

To remove incorrect courses SSH into the server and prepare a `courses-to-delete.txt` 
file that looks like the following:

```
course-v1:Microsoft+AZURE202x+course
course-v1:Microsoft+AZURE203x+course
course-v1:Microsoft+AZURE204x+course
course-v1:PartnerFY18Q2+AZURE205x+course
course-v1:PartnerFY18Q2+AZURE206x+course
course-v1:Lithan+AZURE207x+course
****course-v1:Lithan+AZURE208x+course
course-v1:Lithan+AZURE209x+course
```

The execute the following command:

```bash
$ curl https://raw.githubusercontent.com/appsembler/msft-courses/master/delete.sh | bash
```

**Pro Tip:**
 - There's a deliberate 10 seconds window before the actual course deletion starts.
   During that window a countdown is displayed, during which you can cancel the deletion safely via
   `Ctrl+C`.


## Correcting Course IDs
**Heads Up!**
 - This part is not tested very well. However, you're highly encouraged to test, use and improve to make it stable.
 - This is rather dangerous process by definition. Please read the scripts and make sure you understand what they do
   before continuing.

### Why the IDs Change?
We've had multiple incidents where organizations have imported Microsoft courses by themselves with incorrect IDs. 
Then invited learners to those courses only to discover that Microsoft Achievement Services won't work.

### How to Change Course IDs
Since Open edX does not support course ID change, here's how to change the courses IDs:

 - Coordinate a 4 hour downtime with the customer
 - Once you have the customer approvals, continue with the following steps
 - Take the site down: `$ supervisorctl stop all`
 - Take backups of both MongoDB and MySQL databases
 - Download the MySQL backup into the edxapp machine, if the backup is stored elsewhere and name it `pre.sql`

   Prepare the two files needed for the import:
   
   A) The new file names, run the following command:
   
   ```bash
   $ find . -name '*.tar.gz' -or -name '*.zip' -exec basename {} \; | tee new-ids.txt
   ```
   
   The `new-filenames.txt` file should look like the following:
   ```
   Implementing ETL with SQL Server Integration Services-DAT217x-2017_T4.tar.gz
   Introduction to Artificial Intelligence-DAT263x-2017_T4.tar.gz
   Essential Statistics for Data Analysis using Excel-DAT222x-2017_T4.tar.gz
   Introduction to CSharp-DEV204.1x-2017_T4.tar.gz
   Implementing Predictive Analytics with Spark in Azure HDInsight-DAT20.tar.gz2.3x-2017_T4
   Interpreting and Communicating Data Insights in Business-DAT212x-2017.tar.gz_T4
   Processing Big Data with Hadoop in Azure HDInsight-DAT202.1x-2017_T4.tar.gz
   ...
   ```
   
   B) The old courses IDs file, run the following command:
   ```bash
   $ sudo -Hsu edxapp -- /bin/bash
   $ cd /edx/app/edxapp/edx-platform
   $ source ../edxapp_env
   $ python manage.py lms --settings=aws_appsembler dump_course_ids | tee old-ids.txt
   ```
   
   The `old-ids.txt` should look like the following:
   ```
   course-v1:AJ+Sulfur+2017
   course-v1:edX+Demo+101
   course-v1:PartnerFY18Q2+AZURE205x+course
   course-v1:PartnerFY18Q2+AZURE206x+course
   course-v1:Lithan+AZURE207x+course
   course-v1:Lithan+AZURE208x+course
   course-v1:Lithan+AZURE209x+course
   ```

 - *Manually* clean up the files from unnecessary courses by removing any course that you don't need to rename, otherwise the import could be problematic. 
 - Once the files are prepared, continue with the steps below: 
 - Import the courses correctly via the `import.sh` script above
 - Remove the old courses via the `delete.sh` script above

 
 - Replace the courses IDs with the database backup:
   ```bash
   $ curl https://raw.githubusercontent.com/appsembler/msft-courses/master/replace.sh | bash
   ```
 
 - It will produce a `post.sql` file (unless there's an error, which means that the courses IDs/filenames don't match)
 - Import the database backups:
   ```bash
   $ sudo mysql -u root --default-character-set=utf8 < post.sql
   ```

 - Alternatively, use the following command if the above fails, however this could slightly corrupt the data:
   ```bash
   $ cat post.sql | sed -e 's/INSERT INTO /INSERT IGNORE INTO /' | sudo mysql -u root --default-character-set=utf8
   ```
 
 - Bring the site up again: `$ supervisorctl start all`
 - Inform the customer that you're done


## About
Author Omar Al-Ithawi <omar@appsembler.com>

Please feel free to open issues and pull requests.
