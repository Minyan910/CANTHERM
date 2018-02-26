#!/usr/bin/env python
'''
    Copyright (C) 2018, Sandeep Sharma and James E. T. Smith

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import pdb
import readGeomFc
from Harmonics import *
from scipy import *
import scipy.linalg
#import random
import geomUtility
import os
from constants import *
import numpy as np
import Rotor

class Molecule:
    # has other attributes
    # geom, Mass, Fc, linearity, Energy, Etype, extSymm, nelec, rotors,
    # potentialFile, Iext, ebase, bonds

    def __init__(self, file, isTS):
        self.Freq = []
        self.Harmonics = []
        self.hindFreq = []
        self.bonds = []
        self.Etype = ''
        self.TS = isTS
        line = readGeomFc.readMeaningfulLine(file)
        self.linearity = line.split()[0].upper

# read linearity
        line = readGeomFc.readMeaningfulLine(file)
        linearlity = line.split()[0].upper

# read geometry
        line = readGeomFc.readMeaningfulLine(file)
        tokens = line.split()
        if tokens[0].upper() != 'GEOM':
            print(tokens)
            print('Geom keyword not found in the input file')
            exit()

        if len(tokens) == 1:
            # geometry is given following the GEOM keyword
            line = readGeomFc.readMeaningfulLine(file)
            numAtoms = int(line.split()[0])
            for i in range(numAtoms):
                line = readGeomFc.readMeaningfulLine(file)
                tokens = line.split()
                self.geom[j, 0] = double(tokens[3])
                self.geom[j, 1] = double(tokens[4])
                self.geom[j, 2] = double(tokens[5])
                if (int(tokens[1]) == 6):
                    self.Mass[j] = 12.00000
                if (int(tokens[1]) == 8):
                    self.Mass[j] = 15.99491
                if (int(tokens[1]) == 1):
                    self.Mass[j] = 1.00783
                if (int(tokens[1]) == 7):
                    self.Mass[j] = 14.0031
                if (int(tokens[1]) == 17):
                    self.Mass[j] = 34.96885
                if (int(tokens[1]) == 16):
                    self.Mass[j] = 31.97207
                if (int(tokens[1]) == 9):
                    self.Mass[j] = 18.99840

        # read geometry from the file
        if tokens[1].upper() == 'FILE':
            print("reading Geometry from the file: ", tokens[2])
            geomFile = open(tokens[2], 'r')
            (self.geom, self.Mass) = readGeomFc.readGeom(geomFile)
            # print self.geom
        else:
            print(
                'Either give geometry or give keyword File followed by the file containing geometry data')
            exit()

        self.calculateMomInertia()

# read force constant or frequency data
        line = readGeomFc.readMeaningfulLine(file)
        tokens = line.split()
        if tokens[0].upper() == 'FORCEC' and tokens[1].upper() == 'FILE':
            fcfile = open(tokens[2], 'r')
            self.Fc = readGeomFc.readFc(fcfile)

            for i in range(0, 3 * self.Mass.size):
                for j in range(i, 3 * self.Mass.size):
                    self.Fc[i, j] = self.Fc[j, i]

        elif tokens[0].upper() == "FREQ" and len(tokens) == 1:
            line = readGeomFc.readMeaningfulLine(file)
            numFreq = int(line.split()[0])
            i = 0
            while (i < numFreq):
                line = readGeomFc.readMeaningfulLine(file)
                tokens = line.split()
                i = i + len(tokens)
                for j in tokens:
                    if float(j) < 0 and self.TS:
                        print("Imaginary Freq", j)
                        self.imagFreq = float(j)
                        continue
                    self.Freq.append(float(j))

            if len(self.Freq) > numFreq:
                print('More frequencies than ', numFreq, ' are specified')


        elif tokens[0].upper() == "FREQ" and tokens[1].upper() == "FILE":
            freq_raw = readGeomFc.read_freq(tokens[2])
            for freq in freq_raw:
                if freq < 0 and self.TS:
                    self.imagFreq = freq
                else:
                    self.Freq.append(freq)

        else:
            print('Frequency information cannot be read, check input file again')
            exit()

# read energy
        line = readGeomFc.readMeaningfulLine(file)
        tokens = line.split()
        if (tokens[0].upper() != 'ENERGY'):
            print('Energy information not given')
            exit()
        if tokens[1].upper() == 'FILE':
            print('Reading energy from file: ', tokens[2])
            if (tokens[3].upper() == 'CBS-QB3'):
                self.Etype = 'cbsqb3'
            elif (tokens[3].upper() == 'G3'):
                self.Etype = 'g3'
            elif (tokens[3].upper() == 'UB3LYP'):
                self.Etype = 'ub3lyp'
            elif (tokens[3].upper() == 'DF-LUCCSD(T)-F12'):
                self.Etype= 'DF-LUCCSD(T)-F12'
            self.Energy = readGeomFc.readEnergy(tokens[2], self.Etype)
            print(self.Energy, self.Etype)
        elif (len(tokens) == 3):
            self.Energy = float(tokens[1])
            if (tokens[2].upper() == 'CBS-QB3'):
                self.Etype = 'cbsqb3'
            elif (tokens[2].upper() == 'G3'):
                self.Etype = 'g3'
            elif (tokens[2].upper() == 'UB3LYP'):
                self.Etype = 'ub3lyp'
            print(self.Etype.upper(), ' Energy: ', self.Energy)
        else:
            print('Cannot read the Energy')
            exit()

# read external symmetry
        line = readGeomFc.readMeaningfulLine(file)
        if (line.split()[0].upper() != 'EXTSYM'):
            print('Extsym keyword required')
            exit()
        self.extSymm = int(line.split()[1])

# read electronic degeneracy
        line = readGeomFc.readMeaningfulLine(file)
        if (line.split()[0].upper() != 'NELEC'):
            print('Nelec keyword required')
            exit()
        self.nelec = int(line.split()[1])

# read rotor information
#         line = readGeomFc.readMeaningfulLine(file)
#         if (line.split()[0].upper() != 'ROTORS'):
#             print('Rotors keyword required')
#             exit()
#         self.numRotors = int(line.split()[1])
#         if self.numRotors == 0:
#             self.rotors = []
#             if (len(self.Freq) == 0):
#                 # calculate frequencies from force constant
#                 self.getFreqFromFc()
#             return
#
#         rotorFile = line.split()[2]
#         inertiaFile = open(rotorFile, 'r')
#         # print self.Mass
#         (self.rotors) = readGeomFc.readGeneralInertia(inertiaFile, self.Mass)
#         if len(self.rotors) - 1 != self.numRotors:
#             print("The number of rotors specified in file, ",
#                   rotorFile, ' is different than, ', self.numRotors)
#
#         if (len(self.Freq) == 0):
#             # calculate frequencies from force constant
#             self.getFreqFromFc()
#
#
# # read potential information for rotors
#         line = readGeomFc.readMeaningfulLine(file)
#         tokens = line.split()
#         if tokens[0].upper() != 'POTENTIAL':
#             print('No information for potential given')
#             exit()
#
#         if tokens[1].upper() == 'SEPARABLE':
#             if tokens[2].upper() == 'FILES':
#                 line = readGeomFc.readMeaningfulLine(file)
#                 tokens = line.split()
#                 if len(tokens) != self.numRotors:
#                     print('give a separate potential file for each rotor')
#                 for files in tokens:
#                     Kcos = []
#                     Ksin = []
#                     harmonic = Harmonics(5, Kcos, Ksin)
#                     harmonic.fitPotential(files)
#                     self.Harmonics.append(harmonic)
#
#             elif tokens[2].upper() == 'HARMONIC':
#                 for i in range(self.numRotors):
#                     line = readGeomFc.readMeaningfulLine(file)
#                     numFit = int(line.split()[0])
#                     Ksin = []
#                     Kcos = []
#                     for i in range(numFit):
#                         line = readGeomFc.readMeaningfulLine(file)
#                         tokens = line.split()
#                         Kcos.append(tokens[0])
#                         Ksin.append(tokens[0])
#                     harmonic = Harmonics(numFit, Kcos, Ksin)
#                     self.Harmonics.append(harmonic)
#
#         elif tokens[1].upper() == 'NONSEPARABLE':
#             line = readGeomFc.readMeaningfulLine(file)
#             self.potentialFile = line.split()[0]

        # Rotors
        line = readGeomFc.readMeaningfulLine(file)
        tokens = line.split()

        if tokens[0].upper() != 'ROTORS':
            print('No information for the potential given.\nExiting...')
            exit()

        self.numRotors = int(line.split()[1])

        if self.numRotors > 0:
            line = readGeomFc.readMeaningfulLine(file)
            tokens = line.split()

            if len(tokens) != self.numRotors:
                print('Number of files doesn\'t match the number of rotors.')
                print('Exiting...')
                exit()

            self.rotors = []
            for i in range(self.numRotors):
                rotori = Rotor.Rotor(tokens[i])


# read the bonds
        # line = readGeomFc.readMeaningfulLine(file)
        # tokens = line.split()
        # for bond in tokens:
        #     self.bonds.append(float(bond))

#*************************************************************************

    def getFreqFromFc(self):
        Fc = self.Fc.copy()
        rotors = self.rotors
        numRotors = self.numRotors
        geom = self.geom
        Mass = self.Mass

        if numRotors > 0:
            intRotMatrix = matrix(
                array(zeros((3 * Mass.size, numRotors), dtype=float)))

        inttranrot = matrix(zeros((3 * Mass.size, 6 + numRotors), dtype=float))

        # form cartesian vectors for all rotors
        for i in range(numRotors):
            rotor = rotors[i + 1]
            e12 = matrix('0 0 0')
            e21 = matrix('0 0 0')
            e12 = geom[rotor.pivotAtom - 1, :] - geom[rotor.pivot2 - 1, :]
            e12 = e12 / linalg.norm(e12)
            e21 = -e12
            atoms1 = rotor.atomsList
            for j in atoms1:
                e31 = geom[j - 1, :] - geom[rotor.pivotAtom - 1, :]
                intRotMatrix[3 * (j - 1):3 * j, i] = transpose(cross(e31, e12))

        # make all the modes of unit length
        for i in range(numRotors):
            intRotMatrix[:, i] = intRotMatrix[:, i] / \
                linalg.norm(intRotMatrix[:, i])

        # make the int Rotors Orthonormal
        if numRotors > 0:
            intRotMatrix = matrix(scipy.linalg.orth(intRotMatrix))

        # make translation and rotation unit vectors
        tranrot = matrix(zeros((3 * Mass.size, 6), dtype=float))
        for i in range(Mass.size):
            tranrot[3 * i, 0] = 1.0
            tranrot[3 * i + 1, 1] = 1.0
            tranrot[3 * i + 2, 2] = 1.0

            tranrot[3 * i:3 * i + 3,
                    3] = transpose(matrix([0, -geom[i, 2], geom[i, 1]]))
            tranrot[3 * i:3 * i + 3,
                    4] = transpose(matrix([geom[i, 2], 0, -geom[i, 0]]))
            tranrot[3 * i:3 * i + 3,
                    5] = transpose(matrix([-geom[i, 1], geom[i, 0], 0]))

        tranrot = matrix(scipy.linalg.orth(tranrot))

        inttranrot = matrix(zeros((3 * Mass.size, 6 + numRotors), dtype=float))
        if numRotors > 0:
            inttranrot[:, 0:numRotors] = intRotMatrix
        inttranrot[:, numRotors:numRotors + 6] = tranrot

        inttranrot = matrix(scipy.linalg.orth(inttranrot))

        P = inttranrot * transpose(inttranrot)
        I = matrix(eye(3 * Mass.size, 3 * Mass.size))

        Fc = (I - P) * Fc * (I - P)

        Tcmc = mat(zeros((3 * Mass.size, 3 * Mass.size), dtype=float))
        for i in range(Mass.size):
            for j in range(3):
                Tcmc[(i) * 3 + j, (i) * 3 + j] = 1.0 / sqrt(Mass[i])

        Fc = Tcmc * (Fc * Tcmc)

        [l, v] = linalg.eigh(Fc)

        v = Tcmc * v

        for i in range(3 * Mass.size):
            v[:, i] = v[:, i] / linalg.norm(v[:, i])

        num = Mass.size
        l = sort(l)
        if self.TS:
            self.imagFreq = -1 * sqrt(-1 * l[0] * (ha_to_kcal * 4180 / N_avo) * (
                1.88972e10**2) * (1 / 1.67e-27)) / 2 / math.pi / 3e10
        l = l[6 + numRotors + int(self.TS):]

        for i in range(3 * Mass.size - 6 - numRotors - int(self.TS)):
            self.Freq.append(sqrt(l[i] * (ha_to_kcal * 4180. / N_avo)
                                  * (1.88972e10**2) * (1. / 1.67e-27)) / 2. / math.pi / 3.e10)
            self.Freq[-1]

        Fc = self.Fc.copy()
        Fc = P * Fc * P
        Fc = Tcmc * Fc * Tcmc
        [l, v] = linalg.eigh(Fc)
        l = sort(l)
        l = l[-numRotors:]
        for i in range(numRotors):
            self.hindFreq.append(sqrt(l[i] * (ha_to_kcal * 4180 / N_avo)
                                      * (1.88972e10**2) * (1 / 1.67e-27)) / 2 / math.pi / 3e10)

        # for i in range(len(l)/3+1):
        #    for j in range(3):
        #      if 3*i+j <len(l):
        #        print '%10.3f'%(sqrt(l[3*i+j] * (ha_to_kcal*4180/N_avo)  * (1.88972e10**2) * (1/1.67e-27) )/2/math.pi/3e10),
        #    print

        # print

#*************************************************************************
    def print_thermo_heading(self, oFile, heading):
        l = len(heading) + 4
        symb = '='
        header = footer = symb * l
        mainline = '\n%s %s %s\n' % (symb, heading, symb)
        oFile.write(header + mainline + footer + "\n\n")
        return


#*************************************************************************

    def print_thermo_contributions(self,oFile,Temp,ent,cp,dH):
        # TODO Still need to check the units on these quantities
        # horizontal_line = '===========    =========    ==========    ========\n'
        horizontal_line = '='*12 + " "*3
        horizontal_line *= 4
        horizontal_line += '\n'

        oFile.write(horizontal_line)
        temp_string = 'Temp'
        temp_units_string = 'K'
        ent_string = 'S'
        ent_units_string = 'cal/(mol K)'
        cp_string = 'Cp'
        cp_units_string = 'cal/(mol K)'
        h_string = 'dH'
        h_units_string = 'kcal/mol'

        oFile.write('{:^12}   {:^12}   {:^12}   {:^12}\n'.format(temp_string,ent_string,cp_string,h_string))
        oFile.write('{:^12}   {:^12}   {:^12}   {:^12}\n'.format(temp_units_string,ent_units_string,cp_units_string,h_units_string))
        oFile.write(horizontal_line)

        for i in range(len(Temp)):
            oFile.write('{:^12}'.format(Temp[i]) + "   ")
            oFile.write('{:^12.2f}'.format(ent[i]) + "   ")
            oFile.write('{:^12.2f}'.format(cp[i]) + "   ")
            oFile.write('{:^12.2f}\n'.format(dH[i]))

        oFile.write(horizontal_line + '\n')
        return

#*************************************************************************

    def printData(self, oFile):
        geom = self.geom
        Mass = self.Mass
        oFile.write('Geometry:\n')
        oFile.write('%10s' % 'Mass(amu)' + '%10s' % 'X(ang)' + '%10s' %
                    'Y(ang)' + '%10s' % 'Z(ang)' + '\n')
        for i in range(Mass.size):
            oFile.write('%10.3f' % float(Mass[i]) + '%10.4f' % float(
                geom[i, 0]) + '%10.4f' % float(geom[i, 1]) + '%10.4f' % float(geom[i, 2]) + '\n')

        oFile.write('\nFrequencies (cm-1):\n')
        Freq = self.Freq
        if self.TS:
            oFile.write('Imaginary Frequency: ' + str(self.imagFreq) + '\n')
        for i in range(int(len(Freq) / 3) + 1):
            for j in range(3):
                if 3 * i + j < len(Freq):
                    oFile.write('%10.3f' % Freq[3 * i + j])
            oFile.write('\n')
        oFile.write('\nExternal Symmetry = ' + str(self.extSymm) + '\n')
        oFile.write('Principal Moments of Inertia = ' +
                    str(self.Iext[0]) + '  ' + str(self.Iext[1]) + '  ' + str(self.Iext[2]) + '\n')
        oFile.write('Electronic Degeneracy = ' + str(self.nelec) + '\n')

        if self.numRotors == 0:
            return
        oFile.write(
            '\nFitted Harmonics V(p) = sum (A_i cos(i*p) + B_i sin(i*p)) :\n')

        k = 1
        K = geomUtility.calculateD32(self.geom, self.Mass, self.rotors)
        for harmonic in self.Harmonics:
            oFile.write('Harmonic ' + str(k) + '\n')
            oFile.write('Moment of Inertia: ' + str(float(K[k - 1])) + '\n')
            oFile.write('Symmetry ' + str(self.rotors[k].symm) + '\n')
            oFile.write('BarrierHeight ' + str(harmonic.A) + '\n')
            oFile.write('%12s' % 'A_i' + '%12s' % 'B_i' + '\n')
            for j in range(5):
                oFile.write('%12.3e' %
                            harmonic.Kcos[j] + '%12.3e' % harmonic.Ksin[j] + '\n')
            oFile.write('\n')
            k = k + 1


#*************************************************************************

    def getTranslationThermo(self, oFile, Temp):
        ent = []
        cp = []
        dH = []
        self.print_thermo_heading( oFile, 'Translational Contributions')

        i = 0
        for T in Temp:
            ent.append(R_kcal* math.log((2.0 * math.pi * self.Mass.sum() * amu *
                                     kb * T / h**2)**(1.5) * (kb * T * math.e**(2.5) / 1.013e5)))
            i = i + 1

        i = 0
        for T in Temp:
            cp.append(5.0 / 2 * R)
            i = i + 1

        i = 0
        for T in Temp:
            dH.append(5.0 / 2 * R_kcal* T / 1000.0)
            i = i + 1

        self.print_thermo_contributions(oFile,Temp,ent,cp,dH)

        return ent, cp, dH

#*************************************************************************

    def getVibrationalThermo(self, oFile, Temp, scale):
        # print("SCALE: ", scale) TODO
        ent = []
        cp = []
        dH = []
        parti = []

        self.print_thermo_heading(oFile,'Vibrational Contributions' )
        Freq = []
        for freq in self.Freq:
            Freq.append(freq * scale)

        for T in Temp:
            ent.append(0.0)
            parti.append(1.0)

        # get vibrational contribution to entropy
        j = 0

        for freq in Freq:
            i = 0
            f = 'Freq: ' + '%2.0f' % (j + 1)

            for T in Temp:
                s = -R_kcal* math.log(1.0 - math.exp(-h * freq * 3.0e10 / kb / T))
                s = s + N_avo * (h * freq * 3.0e10 / T) / \
                    (math.exp(h * freq * 3.0e10 / kb / T) - 1.0) / 4.18
                # oFile.write('%12.2f'%s)
                ent[i] = ent[i] + s
                parti[i] = parti[i] * 1.0 / \
                    (1.0 - math.exp(-h * freq * 3.0e10 / kb / T))
                i = i + 1
            j = j + 1

        for T in Temp:
            cp.append(0.0)

        j = 0
        for freq in Freq:
            i = 0
            f = 'Freq: ' + '%2.0f' % (j + 1)
            for T in Temp:
                c = R_kcal* (h * freq * 3.0e10 / kb / T)**2 * math.exp(h * freq *
                                                                   3.0e10 / kb / T) / (1.0 - math.exp(h * freq * 3.0e10 / kb / T))**2
                cp[i] = cp[i] + c
                i = i + 1
            j = j + 1

        for T in Temp:
            dH.append(0.0)

        j = 0
        for freq in Freq:
            i = 0
            f = 'Freq: ' + '%2.0f' % (j + 1)
            for T in Temp:
                h1 = N_avo * (h * freq * 3.0e10) / \
                    (math.exp(h * freq * 3.0e10 / kb / T) - 1.0) / 4180.0 #kcal/mol
                dH[i] = dH[i] + h1
                i = i + 1
            j = j + 1

        self.print_thermo_contributions(oFile,Temp,ent,cp,dH)

        return ent, cp, dH, parti

#*************************************************************************

    def getIntRotationalThermo_PG(self, oFile, Temp):
        ent = []
        cp = []
        dH = []
        seed = 500
        numIter = 100000

        self.print_thermo_heading(oFile,'Internal Rotational Contributions')

        sigma = 1.0
        for rotor in self.rotors:
            sigma = sigma * rotor.symm

        K = geomUtility.calculateD32(self.geom, self.Mass, self.rotors)
        print(K)
        p = 1.0
        a = 1.0
        for T in Temp:
            # print 'Calculating rotational entropy for T: ',T
            Sq = 0.0
            Scl = 0.0
            S = 0.0
            Hq = 0.0
            Hcl = 0.0
            H = 0.0
            cpcl = 0.0
            cpq = 0.0
            Cp = 0.0
            for l in range(self.numRotors):
                sum = 0.0
                vsumexpv = 0.0
                v2sumexpv = 0.0
                minpot = 5.0
                for i in range(numIter):
                    ang = random.rand()
                    pot = self.Harmonics[l].getPotential(ang * 360)
                    if (pot < minpot):
                        minpot = pot

                for i in range(100):
                    ang = i * 360.0 / 100
                    pot = self.Harmonics[l].getPotential(ang) - minpot
                    print(pot)
                    exit()

#                   fi = sqrt(K[l])*exp(-pot*1.0e3/R/T)
                    fi = exp(-pot * 1.0e3 / R_kcal/ T)
                    sum = sum + fi
                    vsumexpv = vsumexpv + pot * 1.0e3 * fi
                    v2sumexpv = v2sumexpv + pot**2 * 1.0e6 * fi
                    average = sum / (i + 1)
                    parti = (2.0 * math.pi * kb * T * amu * 1e-20 / h**2)**(0.5) * \
                        (2 * math.pi) * average / self.rotors[l + 1].symm

                a = a * average
                S = S + R_kcal* math.log(parti) + R_kcal/ 2 + vsumexpv / sum / T
                H = H + R_kcal* T / 2.0 + vsumexpv / sum  # reference to the minimum of the well
                Cp = Cp + R_kcal/ 2.0 + (v2sumexpv * sum -
                                     vsumexpv**2) / sum**2 / R_kcal/ T**2

            sumfreq = 0.0
            for k in range(len(self.hindFreq)):
                harm = self.Harmonics[k]
                ddv = 0.0
                for l in range(5):
                    ddv = ddv - 1 * harm.Kcos[l] * (l + 1)**2
                freq = 1.0 / 2.0 / pi * \
                    sqrt(ddv * 4180.0 / K[k] / 1.0e-20 /
                         amu / N_avo) / 3.0e10
                # print freq, K[l], pi, ddv, K

                Sq = Sq - R_kcal* math.log(1.0 - math.exp(-h * freq * 3.0e10 / kb / T)) + N_avo * (
                    h * freq * 3.0e10 / T) / (math.exp(h * freq * 3.0e10 / kb / T) - 1.0) / 4.18
                Scl = Scl + R_kcal+ R_kcal* math.log(kb * T / h / freq / 3.0e10)
                Hq = Hq + N_avo * (h * freq * 3.0e10) / \
                    (math.exp(h * freq * 3.0e10 / kb / T) - 1.0) / 4.18
                Hcl = Hcl + R_kcal* T
                cpq = cpq + R_kcal* (h * freq * 3.0e10 / kb / T)**2 * math.exp(h * freq *
                                                                           3.0e10 / kb / T) / (1.0 - math.exp(h * freq * 3.0e10 / kb / T))**2
                cpcl = cpcl + R
                sumfreq = sumfreq + freq

            H = H + Hq - Hcl
            S = S + Sq - Scl
            Cp = Cp + cpq - cpcl

            ent.append(S)
            dH.append(H / 1e3)
            cp.append(Cp)

        self.print_thermo_contributions(oFile,Temp,ent,cp,dH)

        return ent, cp, dH

#**************************************************************************

#*************************************************************************

    def getIntRotationalThermo_Q(self, oFile, Temp):
        ent = [0.0] * len(Temp)
        cp = [0.0] * len(Temp)
        dH = [0.0] * len(Temp)
        parti = [1.0] * len(Temp)

        self.print_thermo_heading(oFile, 'Internal Rotation Contributions')

        sigma = 1.0
        for rotor in self.rotors:
            sigma = sigma * rotor.symm

        K = geomUtility.calculateD32(self.geom, self.Mass, self.rotors)
        for irot in range(len(self.rotors) - 1):
            harm = self.Harmonics[irot]
            ddv = 0.0
            for l in range(5):
                ddv = ddv - 1 * harm.Kcos[l] * (l + 1)**2
            freq = 1.0 / 2.0 / pi * \
                sqrt(ddv * 4180.0 / K[irot] / 1.0e-20 / amu / N_avo) / 3.0e10

        # calculate the energy levels for the hindered rotors
        E = self.calculateElevels()
        # pdb.set_trace()
        for iT in range(len(Temp)):
            T = Temp[iT]
            # print T,
            for irot in range(len(self.rotors) - 1):
                sum = 0.0
                vsum = 0.0
                v2sum = 0.0

                for e in E[irot]:
                    e = e - E[irot][0]
                    sum = sum + exp(-e * 1.0e3 / R_kcal/ T)
                    vsum = vsum + e * 1e3 * exp(-e * 1.0e3 / R_kcal/ T)
                    v2sum = v2sum + e**2 * 1e6 * exp(-e * 1.0e3 / R_kcal/ T)

                ent[iT] = ent[iT] + R_kcal* \
                    math.log(sum) + vsum / sum / T - R_kcal* \
                    log(self.rotors[irot + 1].symm)
                dH[iT] = dH[iT] + vsum / sum / 1.0e3
                cp[iT] = cp[iT] + (v2sum * sum - vsum**2) / sum**2 / R_kcal/ T**2
                parti[iT] = parti[iT] * sum


        self.print_thermo_contributions(oFile,Temp,ent,cp,dH)

        return ent, cp, dH, parti

#**************************************************************************

    def calculateElevels(self):
        K = geomUtility.calculateD32(self.geom, self.Mass, self.rotors)
        E = []
        # let us take k = -500, 500
        m = 200
        # print K
        for irot in range(len(self.Harmonics)):
            H = mat(zeros((2 * m + 1, 2 * m + 1), dtype=complex))
            kcos = self.Harmonics[irot].Kcos
            ksin = self.Harmonics[irot].Ksin

            for k in range(0, 2 * m + 1):
                H[k, k] = N_avo * h**2 * (k - m)**2 / 8.0 / math.pi**2 / \
                    K[irot] / amu / 1e-20 / 4180 + self.Harmonics[irot].A

                for n in range(1, 6):
                    if k - n >= 0:
                        H[k, k - n] = kcos[n - 1] / 2 + ksin[n - 1] / 2j
                    if k + n < 2 * m + 1:
                        H[k, k + n] = kcos[n - 1] / 2 - ksin[n - 1] / 2j
            (l, v) = linalg.eigh(H)
            # pdb.set_trace()
            E.append(l)
        return E

#**************************************************************************

    def getExtRotationalThermo(self, oFile, Temp):
        S = []
        ent = []
        cp = []
        dH = []

        self.print_thermo_heading(oFile, "External Rotational Contributions")

        for T in Temp:
            S = log(math.pi**0.5 * exp(1.5) / self.extSymm)
            for j in range(3):
                S = S + \
                    log((8 * math.pi**2 * self.Iext[j]
                         * kb * T * amu * 1e-20 / h**2)**0.5)
            ent.append(S * R)
            cp.append(3.0 * R_kcal/ 2.0)
            dH.append(3.0 * R_kcal* T / 2.0 / 1.0e3)

        self.print_thermo_contributions(oFile,Temp,ent,cp,dH)
        return ent, cp, dH


#**************************************************************************
    def calculateMomInertia(self):
        geom = self.geom
        Mass = self.Mass
        # change coordinates to have cm
        cm = matrix('0.0 0.0 0.0')

        for i in range(Mass.size):
            cm = cm + Mass[i] * geom[i, :]

        cm = cm / sum(Mass)

        for i in range(Mass.size):
            geom[i, :] = geom[i, :] - cm


# calculate moments of inertia
        I = matrix(zeros((3, 3), dtype=double))
        x = array(geom[:, 0])
        y = array(geom[:, 1])
        z = array(geom[:, 2])
        I[0, 0] = sum(array(Mass) * (y * y + z * z))
        I[1, 1] = sum(array(Mass) * (x * x + z * z))
        I[2, 2] = sum(array(Mass) * (x * x + y * y))
        I[0, 1] = I[1, 0] = -sum(array(Mass) * x * y)
        I[0, 2] = I[2, 0] = -sum(array(Mass) * x * z)
        I[1, 2] = I[2, 1] = -sum(array(Mass) * z * y)

# rotate coordinate axes to be parallel to principal axes
        (l, v) = linalg.eigh(I)
        self.Iext = l

#**************************************************************************
    def calculate_Q(self, T):
        '''
        For more details see "Molecular Driving Forces" by Dill Chapters 11
        and 19.
        '''

        # Translational Contrib.
        # TODO Assuming Unimolecular for now so it's technically per volume
        q_tr = np.power((2 * pi * sum(self.Mass) * kb * T)/h**2, 3./2.)

        # Vibrational Contrib.
        q_vib = 1
        for freq in self.Freq:
            q_vib *= 1/( 1 - np.exp(-h * freq * c_in_cm/(kb * T)) )

        # External Rotational Contrib.
        # TODO Add symm. factor
        sigma = 1
        q_rot = np.power(pi * self.Iext[0] * self.Iext[1] * self.Iext[2], 0.5)/sigma
        q_rot *= np.power(8 * pi**2 * kb * T / h**2, 3./2.)

        # print(q_tr,q_vib,q_rot)
        return q_tr * q_vib * q_rot
