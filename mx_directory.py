#!/bin/env python
# -*- coding: utf-8 -*-

# =========================================
# Malcom-X Elementary School
# PTA Family Directory
# =========================================
import os, sys, string, math, random
import datetime
import logging
import datetime

import markdown

import model
import admin

from flask import Flask, render_template, url_for, abort, Markup, request, session, redirect
from flask import escape
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_

# -----------------------------------------------------------
# Config and init app
# -----------------------------------------------------------
app = Flask(__name__)
app.config.from_envvar( 'MXDIR_SETTINGS' )

# Remove any existing loggers
while len(logging.root.handlers):
    logging.root.removeHandler( logging.root.handlers[-1])

# Init logging
logging.basicConfig( filename=app.config['LOGFILE'],
                     format='%(asctime)s %(levelname)s: %(message)s',
                     level=logging.DEBUG )

logging.info("Application Restarted...")


# DBG: also log to console
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
ch.setFormatter(formatter)

logging.getLogger().addHandler(ch)

model.db.app = app
model.db.init_app(app)

# Set up admin interface
admin.init_admin(app)

def modification_date(filename):
    print filename
    if not os.path.exists(filename):
        print "not exist"
        return None

    t = os.path.getmtime(filename)
    print t
    return datetime.datetime.fromtimestamp(t)

def pdfInfo( filename, desc ):

    pdfPath = app.config['PDF_PATH']
    mdate = modification_date( os.path.join(pdfPath,filename) )

    if mdate:
        updDesc = 'Updated '+mdate.strftime( "%b. %-d, %Y")
    else:
        updDesc = 'Not Available'

    return (filename, updDesc, desc )
# -----------------------------------------------------------
#  App Routes
# -----------------------------------------------------------
@app.route('/')
def index():
    classesForGrade = {}
    for cc in  model.Classroom.query.all():

        if not classesForGrade.has_key( cc.grade ):
            classesForGrade[cc.grade] = []

        classesForGrade[cc.grade].append( cc )

    pdfFiles = [
                pdfInfo('mx_directory.pdf', 'MX Directory' ),
                pdfInfo('mx_dir_classsheets.pdf', 'Class Sheets' ),
            ]


    return render_template( "index.html", grades=[ 'K','1','2','3','4','5'],
                            classesForGrade = classesForGrade,
                            pdfFiles=pdfFiles)

@app.route('/classroom/<int:cc_id>')
def classroom( cc_id ):

    classroom = model.Classroom.query.get( cc_id )
    print "Classroom", classroom

    return render_template( "class.html", classroom=classroom )

@app.route('/test')
def test():
    guardians = model.Guardian.query.all()

    for g in guardians:
        print g.firstname, g.lastname, g.email

    return "..."


@app.route('/reset')
def reset():
    model.rebuild_db()
    return "Reset DB..."



# -----------------------------------------------------------
# main for command line
# -----------------------------------------------------------
if __name__ == '__main__':

    # Session
    app.secret_key = app.config['SESSION_KEY']
    app.config['SESSION_TYPE'] = 'filesystem'

    # Uncomment these lines to initialize the database
    # print "Rebuilding database..."
    # model.rebuild_db()
    # sys.exit(1)

    app.run(host='192.168.1.172', debug=True)
    #app.run(host='192.168.1.188', debug=True)
    #app.run( debug=True)	

