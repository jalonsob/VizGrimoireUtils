#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This script parses IRC logs and stores the extracted data in
# a database
# 
# Copyright (C) 2014 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#


from ConfigParser import SafeConfigParser
import MySQLdb

import json
import logging
from optparse import OptionParser
import os.path
import sys
import urllib2, urllib

def read_options():
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1")
    parser.add_option("-u", "--url",
                      action="store",
                      dest="url",
                      default="http://projects.eclipse.org/json/projects/all",
                      help="URL with JSON data for projects")
    parser.add_option("-t", "--tree",
                      action="store_true",
                      dest="tree",
                      default=False,
                      help="Show the projects Tree structure")
    parser.add_option("-s", "--scm",
                      action="store_true",
                      dest="scm",
                      default=False,
                      help="List with git repos")
    parser.add_option("-i", "--its",
                      action="store_true",
                      dest="its",
                      default=False,
                      help="List with bugzilla (its) repos")
    parser.add_option("-m", "--mls",
                      action="store_true",
                      dest="mls",
                      default=False,
                      help="List with mailman repos")
    parser.add_option("-r", "--scr",
                      action="store_true",
                      dest="scr",
                      default=False,
                      help="List with gerrit repos")
    parser.add_option("-d", "--dups",
                      action="store_true",
                      dest="dups",
                      default=False,
                      help="Report about repos duplicated in projects")
    parser.add_option("-p", "--projects",
                      action="store_true",
                      dest="projects",
                      default=False,
                      help="Generate the databases for projects to repositories\
                            and to children mapping")
    parser.add_option("-a", "--automator",
                      action="store",
                      dest="automator_file",
                      help="Automator config file")

    (opts, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("Wrong number of arguments")

    if (opts.projects and not opts.automator_file):
        parser.error("projects option needs automator config file")

    return opts

def getSCMURL(repo):
    basic_scm_url = "http://git.eclipse.org/c"
    url = None
    if repo['path'] is not None:
        if not 'gitroot' in repo['path']:
            logging.warn("Discarding. Can't build URL no git: " + repo['path'])
        else:
            url = basic_scm_url + repo['path'].split('gitroot')[1]
            logging.warn("URL is None. URL built: " + url)
            if (url == "http://git.eclipse.org/c"):
                logging.warn("Discarding. URL path empty: " + url)
                url = None
    return url

def getSCMRepos(project):
    repos = project['source_repo']
    repos_list = []
    for repo in repos:
        if repo['url'] is None:
            url = getSCMURL(repo)
            if url is None: continue
            repos_list.append(url.replace("/c/","/gitroot/"))
        else:
            repos_list.append(repo['url'].replace("/c/","/gitroot/"))
    return repos_list

def parseRepos(repos):
    repos_list = []
    for repo in repos:
        repos_list.append(repo['url'])
    return repos_list

def getITSRepos(project):
    repos = project['bugzilla']
    repos_list = []
    for repo in repos:
        repos_list.append(urllib.unquote(repo['query_url']))
    return repos_list

def getMLSRepos(project):
    repos_list = []
    info = project['dev_list']
    if not isinstance(info, list): # if list, no data
        if info['url'] is not None:
            repos_list.append(info['url'])
    return repos_list

def parseProject(data):
    print("Title: " + data['title'])
    print("ID: "+data['id'][0]['value']) # safe_value other field
    if (len(data['id'])>1):
        logging.info("More than one identifier")
    print("SCM: " + ",".join(getSCMRepos(data)))
    print("ITS: " + ",".join(getITSRepos(data)))
    if not isinstance(data['dev_list'], list):
        if data['dev_list']['url'] is None:
            logging.warn("URL is None for MLS")
        else:
            print("MLS: " + data['dev_list']['url'])
    print("Forums: " + ",".join(parseRepos(data['forums'])))
    print("Wiki: " + ",".join(parseRepos(data['wiki_url'])))
    if (len(data['parent_project'])>1):
        logging.info("More than one parent")
    if (len(data['parent_project'])>0):
        print("Parent: " + data['parent_project'][0]['id'])
    if (len(data['github_repos'])>0):
        print(data['github_repos'])
    print("---")

def getReposList(projects, kind):
    repos_all = []
    for project in projects:
        if kind == "its":
            repos = getITSRepos(projects[project])
        elif kind == "scm":
            repos = getSCMRepos(projects[project])
        elif kind == "mls":
            repos = getMLSRepos(projects[project])
        repos_all += repos
    return repos_all

def getReposDuplicateList(projects, kind):
    repos_dup = {}
    repos_seen = {}

    for project in projects:
        if kind == "its":
            repos = getITSRepos(projects[project])
        if kind == "scm":
            repos = getSCMRepos(projects[project])
        if kind == "mls":
            repos = getMLSRepos(projects[project])
        for repo in repos:
            if repo in repos_seen:
                if not repo in repos_dup:
                    repos_dup[repo] = []
                    repos_dup[repo].append(repos_seen[repo])
                repos_dup[repo].append(project)
            else: repos_seen[repo] = project
    return repos_dup

def showFields(project):
    for key in project:
        print(key)

# We build the tree from leaves to roots
def showProjectsTree(projects):
    import pprint

    tree = {}

    # Add all roots with its leaves
    for key in projects:
        # if (key != "eclipse.platform"): pass
        data = projects[key]
        if (len(data['parent_project']) == 0):
            if not key in tree: tree[key] = []
        else:
            parent = data['parent_project'][0]['id']
            if not parent in tree:
                tree[parent] = []
            tree[parent].append(key)

    pprint.pprint(tree)

def showProjects(projects):
    total_projects = 0

    for key in projects:
        total_projects += 1
        parseProject(projects[key])

    scm_total = len(getReposList(projects, "scm"))
    its_total = len(getReposList(projects, "its"))
    mls_total = len(getReposList(projects, "mls"))
    scm_dup = len(getReposDuplicateList(projects, "scm").keys())
    its_dup = len(getReposDuplicateList(projects, "its").keys())
    mls_dup = len(getReposDuplicateList(projects, "mls").keys())

    logging.info("Total projects: " + str(total_projects))
    # Including all (svn, cvs, git ...)
    logging.info("Total scm: " + str(scm_total) + " (" + str(scm_dup)+ " duplicates)")
    logging.info("Total its: " + str(its_total) + " (" + str(its_dup)+ " duplicates)")
    logging.info("Total mls: " + str(mls_total) + " (" + str(mls_dup)+ " duplicates)")

def showReposSCMList(projects):
    rlist = ""
    all_repos = []
    for key in projects:
        repos = getSCMRepos(projects[key])
        all_repos += repos
    unique_repos = list(set(all_repos))
    rlist += "\n".join(unique_repos)+"\n"
    rlist = rlist[:-1]
    for line in rlist.split("\n"):
        target = ""
        if "gitroot" in line:
            target = line.split("/gitroot/")[1]
        elif "svnroot" in line:
            logging.warning("SVN not supported " + line)
            continue
        else:
            logging.warning("SCM URL special " + line)
        print("git clone " + line + " scm/" + target)

def showReposITSList(projects):
    rlist = ""
    all_repos = []
    for key in projects:
        repos = getITSRepos(projects[key])
        all_repos += repos
    unique_repos = list(set(all_repos))
    rlist += "'"+"','".join(unique_repos)
    rlist += "'"
    print(rlist)

def showReposMLSList(projects):
    rlist = ""
    all_repos = []
    for key in projects:
        repos = getMLSRepos(projects[key])
        all_repos += repos
    unique_repos = list(set(all_repos))
    rlist += "'"+"','".join(unique_repos)
    rlist += "'"
    print(rlist)

def showReposSCRList(projects):
    all_repos = []
    for key in projects:
        repos = getSCMRepos(projects[key])
        all_repos += repos
    unique_repos = list(set(all_repos))
    projects = ""

    for repo in unique_repos:
        if "gitroot" in repo:
            gerrit_project = repo.replace("http://git.eclipse.org/gitroot/","")
            gerrit_project = gerrit_project.replace(".git","")
            projects += "\""+(gerrit_project)+"\""+","
    projects = projects[:-1]
    print(projects)

def showDuplicatesList(projects):
    import pprint
    pprint.pprint(getReposDuplicateList(projects, "its"))
    pprint.pprint(getReposDuplicateList(projects, "scm"))
    pprint.pprint(getReposDuplicateList(projects, "mls"))

def create_projects_schema(cursor):
    project_table = """
        CREATE TABLE projects (
            project_id int(11) NOT NULL AUTO_INCREMENT,
            id varchar(255) NOT NULL,
            title varchar(255) NOT NULL,
            PRIMARY KEY (project_id)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """
    project_repositories_table = """
        CREATE TABLE project_repositories (
            project_id int(11) NOT NULL,
            data_source varchar(255) NOT NULL,
            repository_id int(11) NOT NULL,
            UNIQUE (project_id, data_source, repository_id)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """
    project_children_table = """
        CREATE TABLE project_children (
            project_id int(11) NOT NULL,
            subproject_id int(11) NOT NULL,
            UNIQUE (project_id, subproject_id)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8
    """

    # The data in tables is created automatically.
    # No worries about dropping tables.
    cursor.execute("DROP TABLE IF EXISTS projects")
    cursor.execute("DROP TABLE IF EXISTS project_repositories")
    cursor.execute("DROP TABLE IF EXISTS project_children")

    cursor.execute(project_table)
    cursor.execute(project_repositories_table)
    cursor.execute(project_children_table)

def get_project_children(project_key, projects):
    """returns and array with the project names of its children"""
    children = []
    for project in projects:
        data = projects[project]
        if (len(data['parent_project']) == 0):
            continue
        else:
            parent = data['parent_project'][0]['id']
            if parent == project_key:
                children.append(project)
                children += get_project_children(project, projects)
    return children


def create_projects_db_info(projects, automator_file):
    """Create and fill tables for projects, project_repos and project_children"""

    # Read db config
    parser = SafeConfigParser()
    fd = open(automator_file, 'r')
    parser.readfp(fd)
    fd.close()

    user = parser.get('generic','db_user')
    passwd = parser.get('generic','db_password')
    db = parser.get('generic','db_identities')

    db = MySQLdb.connect(user = user, passwd = passwd, db = db)
    cursor = db.cursor()
    create_projects_schema(cursor)
    logging.info("Projects tables created")

    # First step, load all projects in the table
    projects_db = {}
    for key in projects:
        title = projects[key]['title']
        q = "INSERT INTO projects (title, id) values (%s, %s)"
        cursor.execute(q, (title, key))
        projects_db[key] = db.insert_id()
    logging.info("Projects added")

    # Insert children for all projects
    for project in projects_db:
        children = get_project_children(project, projects)
        for child in children:
            q = "INSERT INTO project_children (project_id, subproject_id) values (%s, %s)"
            project_id = projects_db[project]
            subproject_id = projects_db[child]
            cursor.execute(q, (project_id, subproject_id))
    logging.info("Projects children added")

if __name__ == '__main__':
    opts = read_options()
    metaproject = opts.url.replace("/","_")
    json_file = "./"+metaproject+".json"

    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    logging.info("Starting Eclipse projects analysis from: " +  opts.url)

    if not os.path.isfile(json_file):
        purl = urllib2.urlopen(opts.url)
        projects_raw = purl.read().strip('\n')
        f = open(json_file,'w')
        f.write(projects_raw)
        f.close()
    projects_raw = open(json_file, 'r').read()
    projects = json.loads(projects_raw)
    projects = projects['projects']

    if opts.tree:
        showProjectsTree(projects)
    elif opts.scm:
        showReposSCMList(projects)
    elif opts.its:
        showReposITSList(projects)
    elif opts.mls:
        showReposMLSList(projects)
    elif opts.scr:
        showReposSCRList(projects)
    elif opts.dups:
        showDuplicatesList(projects)
    elif opts.projects:
        create_projects_db_info(projects, opts.automator_file)
    else:
        showProjects(projects)