# Microsoft Courses Tool
Microsoft courses bulk import mini-tool for Open edX installations.

## Usage
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

Run the following command:

```bash
$ curl https://raw.githubusercontent.com/appsembler/msft-courses/master/import.sh | bash
```

Importing a single-course usually takes a minute, so the bulk importing 30 courses usually takes about half an hour.

## Course Import Convention
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

# About
Author Omar Al-Ithawi <omar@appsembler.com>

Please feel free to open issues and pull requests.
