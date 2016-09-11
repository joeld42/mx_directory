#!/bin/env python
# -*- coding: utf-8 -*-

import os, sys, string
import random
import codecs


from flask.ext.sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy.orm import backref, relationship

from sqlalchemy import or_, and_

import model
from model import Family, Address, Phone, Guardian, Student, Classroom, VerifyAddr
from model import db

def importFamilyTSV( filename ):

    # TMP : reset db
    #db.drop_all()
    #db.create_all()

    countAddr = 0
    countParents = 0

    colNum = {}
    totalCols = 0

    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):

        # DBG
        #if countParents > 5:
        #    break

        lsplit = string.split( string.strip(line), '\t' )

        if (firstLine):
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx]
                colNum[cname] = cndx

            firstLine = False

        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            street_from_tsv = model.normalizeAddress( lsplit[colNum['street_from_tsv']] )
            zip_from_tsv = lsplit[colNum['zip_from_tsv']]

            if not street_from_tsv:
                print "MISSING MATCHADDR", line
                continue

            family = Family()
            family.matchAddr = street_from_tsv

            print "---- Family ", family

            countAddr += 1
            print "***", street_from_tsv

            # Use the street_from_tsv as a base address
            baseAddr = Address()
            baseAddr.address1 = street_from_tsv
            baseAddr.zipcode = zip_from_tsv
            baseAddr.city = model.cityFromZip( None, zip_from_tsv)
            #db.session.add( baseAddr )
            #db.session.commit()
            print "ADDING BASEADDR", baseAddr, baseAddr.address1

            defaultAddr = None

            # Now check for up to 4 parent/guardians

            numGuardians = 0
            for i in range(1,5):
                prefix = "p%d_" % i
                firstname = string.strip( lsplit[ colNum[ prefix + "first_name" ]] )
                lastname = string.strip(lsplit[ colNum[ prefix + "last_name" ]] )
                street = string.strip(lsplit[ colNum[ prefix + "street" ]] )
                city = string.strip(lsplit[ colNum[ prefix + "city" ]] )
                zipcode = string.strip(lsplit[ colNum[ prefix + "zip" ]] )
                homephone = string.strip(lsplit[ colNum[ prefix + "home_phone" ]] )
                cellphone = string.strip(lsplit[ colNum[ prefix + "cell_phone" ]] )
                workphone = string.strip(lsplit[ colNum[ prefix + "work_phone" ]] )
                email = string.strip(lsplit[ colNum[ prefix + "email" ]] )

                city = model.cityFromZip( city, zipcode )

                # Any identifier, create a guardian
                if firstname or lastname or email:
                    parent = Guardian()
                    parent.firstname = firstname
                    parent.lastname = lastname
                    parent.email = email
                    parent.family = family

                    countParents += 1

                    print "Import parent ", i, firstname, lastname

                    # Add phones
                    for role, phonenum in [('Home', homephone), ('Work', workphone), ('Cell', cellphone)]:
                        if phonenum:
                            phone = Phone()
                            phone.number = phonenum
                            phone.role = role
                            phone.guardian = parent

                    if street or city or zipcode:

                        # Have address data for this parent, does it
                        # match the base?
                        street = model.normalizeAddress(street)
                        if (street == baseAddr.address1) and (zipcode == baseAddr.zipcode):
                            print "GUARDIAN USES BASE ADDR", baseAddr
                            parent.address = baseAddr
                        else:
                            addr = Address()
                            addr.address1 = street
                            addr.city = city
                            addr.zipcode = zipcode

                            parent.address = addr
                            db.session.add( addr )
                            print "ADDING GUARDIAN ADDR", addr

                        if not defaultAddr:
                            defaultAddr = parent.address
                    else:
                        print "NO ADDR USING DEFAULT"
                        if defaultAddr:
                            parent.address = defaultAddr
                        else:
                            parent.address = baseAddr

                    db.session.add( parent )
                    numGuardians += 1

            # If no names were listed, create an empty guardian
            # for this address
            if (numGuardians==0):

                print "NO GUARDIANS ADDING EMPTY", baseAddr

                parent = Guardian()
                parent.address = baseAddr
                parent.firstname = ''
                parent.lastname = ''
                parent.email = ''
                parent.family = family
                db.session.add(parent)

                countParents += 1

    db.session.commit()

    return "Added %d Families (%d total parent/guardians)" % (countAddr, countParents )



def importStudentTSV( filename ):

    # Delete all of the current students
    Student.query.delete()

    # Delete all the current verify reqs
    VerifyAddr.query.delete()

    db.session.commit()

    stuCount = 0

    colNum = {}
    totalCols = 0

    needVerify = 0

    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):
        lsplit = string.split( string.strip(line), '\t' )


        # if stuCount == 5:
        #     break;

        if (firstLine):
            print lsplit
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx]
                colNum[cname] = cndx

            firstLine = False
        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            firstname = lsplit[ colNum[ "first_name" ] ]
            lastname = lsplit[ colNum[ "last_name" ]]
            matchAddr = lsplit[ colNum[ "street" ]]
            zipcode = lsplit[ colNum[ "zip" ]]
            grade = lsplit[ colNum[ "grade" ]]
            teacher = lsplit[ colNum[ "teacher" ]]

            student = Student()
            student.firstname = firstname
            student.lastname = lastname
            student.zipcode = zipcode

            matchAddr = model.normalizeAddress(matchAddr)

            print "targetAddr is ",matchAddr, zipcode

            # Query any address from their matchAddr
            family = None
            address = Address.query.filter( and_( (Address.address1==matchAddr),
                                                	(Address.zipcode==zipcode)) ).first()

            if not address:
                print "No exact match, trying without zip"
                # didn't find an exact match, first without the zipcode
                address = Address.query.filter( Address.address1==matchAddr).first()

                if address:
                     # Fix the zip code if it's missing
                     if not address.zipcode:
                         print "fixing zip"
                         address.zipcode = student.zipcode
                         db.session.commit()
                     else:
                         print "Mismatched zip codes:", matchAddr, address.zipcode, student.zipcode, "for student", firstname, lastname


            if address:

                for g in address.guardians:
                    if g.family:
                        family = g.family
                        break

                if not family:
                    print "Didn't find guardian for address", address

            else:

                # Didn't find address, flag for hand-verification
                verify = VerifyAddr()
                verify.matchAddr = matchAddr
                verify.zipcode = zipcode
                verify.student = student
                db.session.add( verify )

                needVerify += 1



            if family:
                student.family = family

            # query for their classroom
            room = Classroom.query.filter( and_((Classroom.teacher==teacher),
                                                     (Classroom.grade==grade))).first()
            if not room:
                room = Classroom()
                room.teacher = teacher
                room.grade = grade

                db.session.add( room )

            student.classroom = room

            db.session.add(student)
            stuCount += 1

    db.session.commit()
    return "Imported %d students (%d addresses need verification)..." % (stuCount, needVerify)

def importStudentAndGuardianTSV( filename ):

    # Delete all of the current students and classroom info
    Student.query.delete()
    Classroom.query.delete()

    # Delete all the current verify reqs
    VerifyAddr.query.delete()



    db.session.commit()

    stuCount = 0

    colNum = {}
    totalCols = 0

    needVerify = 0

    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):
        lsplit = string.split( string.strip(line), '\t' )

        # if stuCount == 5:
        #     break

        if (firstLine):
            print lsplit
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx].lower()
                print cname
                colNum[cname] = cndx

            firstLine = False

        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            firstname = lsplit[ colNum[ "first name" ] ]
            lastname = lsplit[ colNum[ "last name" ]]
            matchAddr = lsplit[ colNum[ "mailing address" ]]
            city = lsplit[ colNum["city"]]
            zipcode = lsplit[ colNum[ "zip" ]]
            grade = lsplit[ colNum[ "grade" ]]
            if (grade=='0'):
                grade = 'K'
            room = lsplit[ colNum[ "room" ]]
            teacher = lsplit[ colNum[ "teacher" ]]


            student = Student()
            student.firstname = firstname
            student.lastname = lastname

            matchAddr = model.normalizeAddress(matchAddr)
            print "targetAddr is ",matchAddr, zipcode

            # Query any address from their matchAddr
            # family = None
            # address = Address.query.filter( and_( (Address.address1==matchAddr),
            #                                     	(Address.zipcode==zipcode)) ).first()

            family = Family.query.filter( Family.matchAddr == matchAddr ).first()

            if not family:
                print "No exact match, trying address"
                # didn't find an exact match, first without the zipcode
                address = Address.query.filter( Address.address1==matchAddr).first()

                if address:
                    # Fix the zip code if it's missing
                    if not address.zipcode:
                         print "fixing zip"
                         address.zipcode = zipcode

                    for g in address.guardians:
                        if g.family:
                            family = g.family
                            break

                    if not family:
                        # Shouldn't happen, orphaned address
                        print "Didn't find guardian for address", address

            if not family:

                # Create a new Family entry from the imported contact info
                # Use the street_from_tsv as a base address
                baseAddr = Address()
                baseAddr.address1 = matchAddr
                baseAddr.zipcode = zipcode
                baseAddr.city = model.cityFromZip( None, zipcode)
                db.session.add(baseAddr)

                homePhone = lsplit[ colNum[ "home phone" ]]
                guardianInfo = [ ( lsplit[ colNum[ "mother" ]],
                                   lsplit[ colNum[ "mother email" ]] ),
                                 ( lsplit[ colNum[ "father" ]],
                                   lsplit[ colNum[ "father email" ]] ) ]
                for name, email in guardianInfo:
                    if name:
                        if name.find(',') != -1:
                            lastname, firstname = string.split(name, ',')
                        else:
                            nsplit = string.split(name)
                            firstname = ' '.join(nsplit[:-1])
                            lastname = nsplit[-1]

                        if not family:
                            family = Family()
                            family.matchAddr = matchAddr
                            db.session.add(family)

                        parent = Guardian()
                        parent.firstname = firstname
                        parent.lastname = lastname
                        parent.email = email
                        parent.address = baseAddr

                        parent.family = family
                        db.session.add(parent)

                        if homePhone:
                            phone = Phone()
                            phone.number = homePhone
                            phone.guardian = parent
                            phone.role = 'Home'
                            db.session.add(phone)


                # If not an (incoming) K student, flag for verification
                if True or grade != 'K':

                    verify = VerifyAddr()
                    verify.matchAddr = matchAddr
                    verify.zipcode = zipcode
                    verify.student = student
                    db.session.add( verify )

                    needVerify += 1

            if family:
                student.family = family

            # query for their classroom
            room = Classroom.query.filter( and_((Classroom.teacher==teacher),
                                                     (Classroom.grade==grade))).first()
            if not room:
                room = Classroom()
                room.teacher = teacher
                room.grade = grade

                db.session.add( room )

            student.classroom = room

            db.session.add(student)
            stuCount += 1

    db.session.commit()
    return "Imported %d students (%d addresses need verification)..." % (stuCount, needVerify)

