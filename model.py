#!/bin/env python3
# -*- coding: utf-8 -*-

import string

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from flask_sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy.orm import backref, relationship

from sqlalchemy import or_, and_

db = SQLAlchemy()

ADDR_NORMS = {
    u'Ave' : ['av', 'ave', 'avenue'],
    u'St' : ['st', 'str', 'street'],
    u'Rd' : ['rd', 'road' ],
    u'Way' : ['wy', 'wa', 'way' ],
    u'Terr' : ['terr', 'te', 'ter', 'tr' ]
}

# East Bay Zip codes
ZIPCODES = { 'Albany': ['94706'],
             'Alameda' : ['94501', '94502'],
             'El Sobrante': ['94803', '94820'],
             'Emeryville': ['94608', '94662'],
             'El Cerrito' : ['94530'],
             'Richmond': ['94801', '94802', '94804', '94805', '94807', '94808', '94850'],
             'San Pablo': ['94806'],
             'Berkeley': ['94701', '94702', '94703', '94704', '94705', '94707', '94708', '94709', '94710',
                          '94712', '94720'],
             'Oakland': ['94601', '94602', '94603', '94604', '94605', '94606', '94607', '94609', '94610',
                         '94611', '94612', '94613', '94614', '94615', '94617', '94618', '94619', '94621',
                         '94622', '94623', '94624', '94625', '94649', '94659', '94660', '94661', '94666'],
             'Pinole' : ['94564'],
             'Piedmont': ['94620'] }

ZIPCODES_FLIP = {}
for k, vals in ZIPCODES.items():
    for v in vals:
        ZIPCODES_FLIP[v] = k


# Flip the addr norms list
ADDR_NORMS_REPL = {}
for k, vals in ADDR_NORMS.items():
    for v in vals:
        ADDR_NORMS_REPL[v] = k


def normalizeAddress( addr ):

    #print "normalize ", addr
    addr2 = []
    for part in string.split(string.strip(addr)):

        # Convert chunk to ascii to use as key
        pp = part.encode('ascii','replace').lower()

        if (pp[-1]=='.'):
            pp=pp[:-1]

        addr2.append( ADDR_NORMS_REPL.get( pp, part ))

    addrNorm = u' '.join(addr2)

    #if addr != addrNorm:
    #    print "NORM: ", addr, " -> ", addrNorm

    return addrNorm

def cityFromZip( origCity, zipcode ):

    zipcode = string.strip(zipcode).encode('ascii','replace')
    if not zipcode:
        return origCity

    print (f"Lookup zip {zipcode}, ({origCity})")

    # Echo city back if specified, this is just so we
    # can call this without checking if city is specified
    if origCity:
        print (" -> unchanged", origCity)
        return origCity

    # Check for east bay zip codes
    print(" -> ", ZIPCODES_FLIP.get( zipcode, None ) )
    return ZIPCODES_FLIP.get( zipcode, None )

class Address( db.Model ):

    id = db.Column( db.Integer, primary_key=True )

    address1 = db.Column( db.String(100))
    address2 = db.Column( db.String(100))
    city = db.Column( db.String(20))
    zipcode = db.Column( db.String(10))

    guardians = db.relationship('Guardian',
                                backref='address',
                                lazy='dynamic')

    def displayCity(self):
        cityParts = []
        if self.city:
            cityParts.append(self.city)
        if self.zipcode:
            cityParts.append(self.zipcode)

        if len(cityParts):
            return ' '.join(cityParts)
        else:
            return None

    def __repr__(self):
        fallback = '<blank addr %s>' % str(self.id) if self.id else '<blank addr>'
        return self.address1 if self.address1 else fallback

# This records a "guess" where we don't have an exact match
# for a student's address. These should be hand-checked to clean up
class VerifyAddr( db.Model ):
    id = db.Column( db.Integer, primary_key=True )

    # The address as imported (normalized)
    matchAddr = db.Column( db.String(100))
    zipcode = db.Column( db.String(10))

    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    student = db.relationship( "Student", back_populates="verifyAddr")

    def __repr__(self):
        return str(self.matchAddr)

    def fuzzyResults( self, limit=5 ):

        # Fetch all the address for fuzzy matching
        allAddrsDict = {}
        for addr in Address.query.all():
            if addr.address1:
                allAddrsDict[addr.address1] = addr

        results = []

        usedAddrs = []

        # find exact house number matches
        houseNum = string.split( self.matchAddr )[0]
        for a1 in allAddrsDict.keys():
            h = string.split( a1 )[0]
            if (h==houseNum):
                results.append( (allAddrsDict[a1], 'House number is exact match.') )
                usedAddrs.append( a1 )

        # Look for guardians
        for g in Guardian.query.filter( Guardian.lastname == self.student.lastname ):

            if g.address:
                if not g.address.address1 in usedAddrs:
                    results.append( (g.address, 'Last name matches student.') )
                    usedAddrs.append( g.address.address1 )


        # Rank the best fuzzy matches
        bestMatch = process.extract( self.matchAddr, allAddrsDict.keys() )

        for r in bestMatch[:limit]:

            if not r[0] in usedAddrs:
                results.append( (allAddrsDict[r[0]], 'Fuzzy match with %d strength.' % r[1]) )

        return results

class Family( db.Model ):

    id = db.Column( db.Integer, primary_key=True )

    guardians = db.relationship('Guardian',
                                backref='family',
                                lazy='dynamic')

    students = db.relationship('Student',
                                backref='family',
                                lazy='dynamic')

    matchAddr = db.Column( db.String(100))

    def __repr__(self):
        if self.id:
            return '<Family %d>' % self.id
        else:
            return db.Model.__repr__(self)

class Phone( db.Model ):
    id = db.Column( db.Integer, primary_key=True )

    number = db.Column( db.String(20))
    role = db.Column( db.String(20))

    guardian_id = db.Column(db.Integer, db.ForeignKey('guardian.id'))

    def __repr__(self):

        role = self.role+': ' if self.role else ''
        return role + str(self.number)


# Parent or Guardian
class Guardian( db.Model ):
    id = db.Column( db.Integer, primary_key=True )
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'))
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'))

    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(80))
    email = db.Column(db.String(120))

    phones = db.relationship('Phone', backref='guardian', lazy='dynamic')

    def __repr__(self):
        # Flask-admin doesn't like utf-8 so use ascii for repr, use displayname
        # for user-facing output
        use_id = 0
        if self.id:
            use_id = self.id
        return ('%s %s [#%d]' % (self.firstname, self.lastname, use_id ))

    def displayName(self):
        return ('%s %s' % (self.firstname, self.lastname ))

    def duplicate( self ):

        dupe = Guardian()
        dupe.family_id = self.family_id
        dupe.address_id = self.address_id
        dupe.firstname = self.firstname
        dupe.lastname = self.lastname
        dupe.email = self.email

        db.session.add( dupe )

        for ph in self.phones:
            pdupe = Phone()
            pdupe.role = ph.role
            pdupe.number = ph.number
            pdupe.guardian = dupe
            db.session.add(pdupe)

        db.session.commit()
        return dupe


class Student( db.Model ):
    id = db.Column( db.Integer, primary_key=True )
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'))
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(80))
    student_id = db.Column( db.Integer )

    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'))

    verifyAddr = db.relationship('VerifyAddr',
                                 uselist=False,
                                 back_populates="student"
                                )


    def __repr__(self):
        return (u'%s %s' % (self.firstname, self.lastname ))

    def displayName(self):
        return (u'%s %s' % (self.firstname, self.lastname ))

    def needsVerify(self):
        if self.verifyAddr or not self.family:
            return True
        return False

class Classroom( db.Model ):
    id = db.Column( db.Integer, primary_key=True )
    grade = db.Column(db.String(3))

    teacher = db.Column(db.String(100))

    students = db.relationship('Student',
                                backref='classroom',
                                lazy='dynamic')

    def classFamilies(self ):
        families = set()
        for s in self.students:
            if s.family:
                families.add( s.family )

        classfams = list(families)

        classfams.sort( key=lambda f: f.students[0].firstname or "" )

        return classfams

    def numStudents(self):

        stus = list(self.students)
        return len(stus)

    def __repr__(self):
        return '%s (%s)' % (self.teacher, self.grade );



def rebuild_db():

    db.drop_all()
    db.create_all()