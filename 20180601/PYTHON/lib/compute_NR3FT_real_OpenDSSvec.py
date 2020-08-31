import numpy as np
import opendssdirect as dss
import re
import sys
def compute_NR3FT_real_function(XNR,network,slackidx,Vslack):

    np.set_printoptions(threshold=sys.maxsize)
    # Michael Sankur - msankur@lbl.gov
    # 2018.01.01

    # This function computes the residuals of power flow equations

    # INPUT(S)
    # network - struct containing all pertinent the network information,
    # including all other structs
    # base - struct containing base values
    # nodes - struct containing node parameters
    # lines - struct containing line parameters
    # loads - struct containing load parameters
    # caps - struct containing capacitor parameters
    # cons - struct containing controller parameters
    # vvc - struct containing vvc parameters
    # slackidx - index of slack node
    # slackVnom - voltage reference for slack node

    # OUTPUT(S)
    # FT - Residuals for power flow equations, composed of three parts - see
    # near end of function
    # FTSUBV - residuals of slackbus real and imaginary voltage equation
    # components
    # FTKVL - residuals of KVL real and imaginary equation components
    # FTKCL - residuals of KCL real and imaginary equation components

    # slackidx is the node index of the slack bus, which is assigned a fixed
    # voltage reference of slackVnom.

    # Voltage and current are separated into their real and imaginary parts
    # V_n^phi = A_n^phi + j B_n^phi
    # I_n^phi = C_n^phi + j D_n^phi

    # Voltage and current vectors for a single phase
    # V^phi = [A_1^phi, B_1^phi, A_2^phi, B_2^phi, ... , A_n^phi, B_n^phi]
    # I^phi = [C_1^phi, D_1^phi, C_2^phi, D_2^phi, ... , C_n^phi, D_n^phi]

    # The NR algorithm variable
    # X = [V^a V^b V^c I^a I^b I^c]

    '''
    base = network.base
    nodes = network.nodes
    lines = network.lines
    configs = network.configs
    loads = network.loads
    caps = network.caps
    cons = network.cons
    vvc = network.vvc
    '''

    # node parameters
    nnode = network.nodes.nnode
    NPH = network.nodes.PH
    inlines = network.nodes.inlines
    innodes = network.nodes.innodes
    outlines = network.nodes.outlines
    outnodes = network.nodes.outnodes

    # line paramters
    nline = network.lines.nline

    LPH = network.lines.PH
    TXnum = network.lines.TXnum
    RXnum = network.lines.RXnum
    FZpu = network.lines.FZpu
    FRpu = network.lines.FRpu
    FXpu = network.lines.FXpu

    # load parameters
    spu = network.loads.spu
    APQ = network.loads.aPQ
    AI = network.loads.aI
    AZ = network.loads.aZ

    # capacitor paramters
    cappu = network.caps.cappu

    # controller parameters
    wpu = network.cons.wpu

    # vvc parameters
    vvcpu = network.vvc.vvcpu

    dss.run_command('Redirect compare_opendss_05node_threephase_unbalanced_oscillation_03.dss')
    dss.Solution.Solve()
    nline = len(dss.Lines.AllNames())
    nnode = len(dss.Circuit.AllBusNames())
    # Residuals for slack node voltage

    def bus_phases(): #goes through all the buses and saves their phases to a list stored in a dictionary
    #1 if phase exists, 0 o.w.
    #list goes [a, b, c]
    #key is the bus name (without the phase part)
        dictionary = {}
        for k2 in range(len(dss.Circuit.AllNodeNames())):
            for i in range(1, 4):
                pattern = r"\.%s" % (str(i))

                m = re.findall(pattern, dss.Circuit.AllNodeNames()[k2])
                a, b = dss.Circuit.AllNodeNames()[k2].split('.')
                if m and a in dictionary:
                    temp = dictionary[a]
                    temp[i - 1] = 1
                    dictionary[a] = temp
                elif m and a not in dictionary:
                    dictionary[a] = [0, 0, 0]
                    temp = dictionary[a]
                    temp[i - 1] = 1
                    dictionary[a] = temp
        return dictionary

    A_m = np.array([])
    B_m = np.array([])

    C_mn = np.array([])
    D_mn = np.array([])

    R_matrix = np.zeros((nline,9))
    X_matrix = np.zeros((nline,9))

    dss.Circuit.SetActiveBus(dss.Circuit.AllBusNames()[0])
    kV_base = dss.Bus.kVBase()

    bus_phase_dict = bus_phases()
    def identify_line_phases(line): #figures out which phases correspond to a line
    #(for assigning rmatrix based on line code)
    #returns list of 0's 1's whether or not phase exists in line
        k = np.zeros(3)
        dss.Lines.Name(line)
        bus = dss.Lines.Bus1()
        for i in range(1, 4):
            pattern = r"\.%s" % (str(i))
            m = re.findall(pattern, bus)
            if m:
                k[i - 1] = 1
        return k

    for k1 in range(len(dss.Circuit.AllBusNames())):
        dss.Circuit.SetActiveBus(dss.Circuit.AllBusNames()[k1])
        phases = bus_phase_dict[dss.Circuit.AllBusNames()[k1]]
        volts = dss.Bus.PuVoltage() #get bus1's puVoltage
        a_temp = np.zeros(3)
        b_temp = np.zeros(3)

        count = 0
        for i in range(0, 3):
            if phases[i] == 1: #need to properly assign voltages based on what phases exist
                a_temp[i] = volts[count]
                b_temp[i] = volts[count+1]
                count = count + 2

        A_m = np.append(A_m, a_temp) #split into re/im parts
        B_m = np.append(B_m, b_temp)


    for k2 in range(len(dss.Lines.AllNames())):
        dss.Lines.Name(dss.Lines.AllNames()[k2]) #set the line

        linecode = dss.Lines.LineCode() #get the linecode
        dss.LineCodes.Name(linecode) #set the linecode
        xmat = dss.LineCodes.Xmatrix() #get the xmat
        rmat = dss.LineCodes.Rmatrix() #get the rmat
        line_phases = identify_line_phases(dss.Lines.AllNames()[k2])

        if len(xmat) == 9:
            for i in range(len(xmat)):
                X_matrix[k2][i] = xmat[i] #fill x/r where they are shaped like nline x 9 (for 9 components)
                R_matrix[k2][i] = rmat[i]
        elif len(xmat) == 1:
            X_matrix[k2][0] = xmat[0]
            X_matrix[k2][4] = xmat[0]
            X_matrix[k2][8] = xmat[0]
            R_matrix[k2][0] = rmat[0]
            R_matrix[k2][4] = rmat[0]
            R_matrix[k2][8] = rmat[0]
        elif len(xmat) == 4:
            xmat = np.reshape(xmat, (2,2))
            rmat = np.reshape(rmat, (2,2))
            if line_phases[0] == 0:
                xmatt = np.vstack([np.zeros((1,2)),xmat[:,:]])
                xmatt2 = np.hstack((np.zeros((3,1)), xmatt[:, :]))
                X_matrix[k2, :] = xmatt2.flatten()
                r_temp = np.vstack([np.zeros((1,2)),rmat[:,:]])
                r_temp2 = np.hstack((np.zeros((3,1)), r_temp[:, :]))
                R_matrix[k2, :] = r_temp2.flatten()
            elif line_phases[1] == 0:
                xmatt = np.vstack([np.vstack([xmat[0,:], np.zeros((1,2))]), xmat[len(xmat)-1,:]])
                xmatt2 = np.hstack((np.hstack((np.reshape(xmatt[:, 0], (3, 1)), np.zeros((3,1)))), np.reshape(xmatt[:, len(xmatt[0])-1], (3,1))))
                X_matrix[k2, :] = xmatt2.flatten()
                r_temp = np.vstack([np.vstack([rmat[0,:], np.zeros((1,2))]), rmat[len(xmat)-1,:]])
                r_temp2 = np.hstack((np.hstack((np.reshape(r_temp[:, 0], (3, 1)), np.zeros((3,1)))), np.reshape(r_temp[:, len(r_temp[0])-1], (3,1))))
                R_matrix[k2, :] = r_temp2.flatten()
            else:
                xmatt = np.vstack([xmat[:,:],np.zeros((1,2))])
                xmatt2 = np.hstack((xmatt[:, :], np.zeros((3,1))))
                X_matrix[k2, :] = xmatt2.flatten()
                r_temp = np.vstack([rmat[:,:],np.zeros((1,2))])
                r_temp2 = np.hstack((r_temp[:, :], np.zeros((3,1))))
                R_matrix[k2, :] = r_temp2.flatten()

        c_temp = np.zeros(3) #retrieve line current
        d_temp = np.zeros(3)

        for i in range(0, 3): #len(dss.CktElement.Currents()), 2): #get the currents of the line

            c_temp[i] = 0
            d_temp[i] = 0
    #         c_temp[i//2] = np.divide(dss.CktElement.Currents()[i], kV_base) #per unit-ify the currents
    #         d_temp[i//2] = np.divide(dss.CktElement.Currents()[i+1], kV_base)
        C_mn = np.append(C_mn, c_temp)
        D_mn = np.append(D_mn, d_temp)

    X = np.array([]) #make X, X.shape = (2*3*(nline+nnode), 1)

    for ph in range(0,3):
        for nodes in range(nnode):
            X = np.append(X, A_m[nodes*3 + ph]) #add a, b by node and then phase
            X = np.append(X, B_m[nodes*3 + ph])

    for ph in range(0, 3):
        for lines in range(nline):
            X = np.append(X, C_mn[lines*3 + ph]) #add c, d by line and then phase
            X = np.append(X, D_mn[lines*3 + ph])

    X = np.reshape(XNR, (2*3*(nnode+nline), 1 ))
    #X = np.reshape(X, (2*3*(nnode+nline), 1))
    #------------ slack bus ------------------

    g_SB = np.array([]) #assumes slack bus is at index 0
    sb_idx = [0, 1, 2*nnode, 2*nnode+1, 3*nnode, 3*nnode+1]
    for i in range(len(sb_idx)):
        temp_row = np.zeros(len(X))
        temp_row[sb_idx[i]] = 1
        g_SB = np.append(g_SB, temp_row)
    g_SB = np.reshape(g_SB, (6, len(g_SB) // 6))

    b_SB = np.array([])
    for i in range(3):
        b_SB = np.append(b_SB, Vslack[i].real)
        b_SB = np.append(b_SB, Vslack[i].imag)
    b_SB = np.reshape(b_SB, (len(b_SB), 1))

    FTSUBV = (g_SB @ X) - b_SB

    #--------------------------------------------------
    # Residuals for KVL across line (m,n)

    R_matrix = R_matrix/network.base.Zbase
    X_matrix = X_matrix/network.base.Zbase

    def get_bus_idx(bus):
        k = -1
        for n in range(len(dss.Circuit.AllBusNames())): #iterates over all the buses to see which index corresponds to bus
            if dss.Circuit.AllBusNames()[n] in bus:
                k = n
        return k

    def identify_bus_phases(bus): #figures out which phases correspond to the bus
    #returns a list of the r/x matrix places that have those phase/s
        k = np.zeros(3)
        for i in range(1, 4):
            pattern = r"\.%s" % (str(i))
            m = re.findall(pattern, bus)
            if m:
                k[i - 1] = 1
        return k

    G_KVL = np.array([])

    for ph in range(0, 3):
        for line in range(len(dss.Lines.AllNames())):
            dss.Lines.Name(dss.Lines.AllNames()[line]) #set the line
            bus1 = dss.Lines.Bus1()
            bus2 = dss.Lines.Bus2()

            bus1_idx = get_bus_idx(bus1) #get the buses of the line
            bus2_idx = get_bus_idx(bus2)

            b1, b2 = dss.CktElement.BusNames() #the buses on a line should have the same phase
            bus1_phases = identify_bus_phases(b1) #identifies which phase is associated with the bus (which is the same as the line)
            temp_row = np.zeros(len(X))
            #real part of KVL residual
            #assigning the re voltage coefficients

            temp_row[2*(nnode)*ph + 2*(bus1_idx)] = 1 #A_m
            temp_row[2*(nnode)*ph + 2*(bus2_idx)] = -1 #A_n
            if bus1_phases[ph] == 1:
                #assigning the summation portion of the residual
                temp_row[2*3*(nnode) + 2*line] = -R_matrix[line][ph*3] * bus1_phases[0] #C_mn for a
                temp_row[2*3*(nnode) + 2*line + 1] = X_matrix[line][ph*3] * bus1_phases[0] #D_mn for a
                temp_row[2*3*(nnode) + 2*nline + 2*line] = -R_matrix[line][ph*3 + 1] * bus1_phases[1] #C_mn for b
                temp_row[2*3*(nnode) + 2*nline + 2*line + 1] = X_matrix[line][ph*3 + 1] * bus1_phases[1] #D_mn for b
                temp_row[2*3*(nnode) + 4*nline + 2*line] = -R_matrix[line][ph*3 + 2] * bus1_phases[2] #C_mn for c
                temp_row[2*3*(nnode) + 4*nline + 2*line + 1] = X_matrix[line][ph*3 + 2] * bus1_phases[2] #D_mn for c
                G_KVL = np.append(G_KVL, temp_row)
            #same as above for imaginary part of KVL residual
            else:
                G_KVL = np.append(G_KVL, temp_row)

            temp_row[2*(nnode)*ph + 2*(bus1_idx) + 1] = 1 #B_m
            temp_row[2*(nnode)*ph + 2*(bus2_idx) + 1] = -1 #B_n
            if bus1_phases[ph] == 1:
                temp_row = np.zeros(len(X))
                temp_row[2*3*(nnode) + 2*line] = -X_matrix[line][ph*3] * bus1_phases[0] #C_mn for a
                temp_row[2*3*(nnode) + 2*line + 1] = -R_matrix[line][ph*3] * bus1_phases[0] #D_mn for a
                temp_row[2*3*(nnode) + 2*nline + 2*line] = -X_matrix[line][ph*3 + 1] * bus1_phases[1] #C_mn for b
                temp_row[2*3*(nnode) + 2*nline + 2*line + 1] = -R_matrix[line][ph*3 + 1] * bus1_phases[1] #D_mn for b
                temp_row[2*3*(nnode) + 4*nline + 2*line] = -X_matrix[line][ph*3 + 2] * bus1_phases[2] #C_mn for c
                temp_row[2*3*(nnode) + 4*nline + 2*line + 1] = -R_matrix[line][ph*3 + 2] * bus1_phases[2] #D_mn for c
                G_KVL = np.append(G_KVL, temp_row)
            else:
                temp_row = np.zeros(len(X))
                G_KVL = np.append(G_KVL, temp_row)
    G_KVL = np.reshape(G_KVL,(2*3*nline, 2*3*(nnode+nline)))
    b_kvl = np.zeros((2*3*nline, 1))
    gx_term = np.reshape((G_KVL @ X), (len(G_KVL@X), 1) )
    FTKVL = (gx_term) - b_kvl

    #---------------------------
    # Residuals for KCL at node m
    # This algorithm assumes that the slack bus has a fixed voltage reference,
    # and its power is "floating" and will be resolved. The slack bus is
    # assumed to be the first node, which respresents the transmission line, or
    # substation if the network configuration is as such - see note below
    #
    # X_cut = X[2:]
    # X_cut = np.append(X_cut[:2*nnode - 2], X_cut[2*nnode:])
    # X_cut = np.append(X_cut[:2*2*nnode -2], X_cut[2*2*nnode:])
    #
    def linelist(busname): #returns two lists of in and out lines at a bus
        in_lines = np.array([])
        out_lines = np.array([])
        for k in range(len(dss.Lines.AllNames())):
            dss.Lines.Name(dss.Lines.AllNames()[k])
            if busname in dss.Lines.Bus1():
                out_lines = np.append(out_lines, dss.Lines.AllNames()[k])
            elif busname in dss.Lines.Bus2():
                in_lines = np.append(in_lines, dss.Lines.AllNames()[k])
        return in_lines,out_lines

    def get_line_idx(line): #returns the index of a line as stored in dss.Lines.AllNames()
        k = -1

        for n in range(len(dss.Lines.AllNames())):
            if dss.Lines.AllNames()[n] == line:
                k = n
        return k

    def d_factor(busname, cplx):
        factor = np.array([])
        k = -1
        for n in range(len(dss.Loads.AllNames())):
            if busname in dss.Loads.AllNames()[n]:
                k = n
        dss.Loads.Name(dss.Loads.AllNames()[n])
        if k == -1:
            d_factor = 0
        elif cplx == 0:
            d_factor = (dss.Loads.kW() + dss.Loads.kvar())*1e3/network.base.Sbase
        elif cplx == 1:
            d_factor = dss.Loads.kvar()*1e3/network.base.Sbase
            d_factor = .03125/network.base.Sbase
        return d_factor

    beta_S = 0.75
    beta_I = 0.1
    beta_Z = 0.15

    H = np.zeros((2 * 3 * (nnode + nline), 2 * 3* (nnode + nline), 2*3*(nnode-1)))
    g = np.zeros((1, 2*3*(nnode+nline), 2*3*(nnode-1)))
    b = np.zeros((1, 1, 2*3*(nnode-1)))

    for ph in range(0,3):
        if ph == 0: #set nominal voltage based on phase
            A0 = 1
            B0 = 0
        elif ph == 1:
            A0 = -1/2
            B0 = -1 * np.sqrt(3)/2
        elif ph == 2:
            A0 = -1/2
            B0 = np.sqrt(3)/2
        for k2 in range(1, len(dss.Circuit.AllBusNames())): #skip slack bus
            dss.Circuit.SetActiveBus(dss.Circuit.AllBusNames()[k2])
            out_lines, in_lines = linelist(dss.Circuit.AllBusNames()[k2]) #get in/out lines of bus
            for cplx in range(0,2):
                load_val = d_factor(dss.Circuit.AllBusNames()[k2], cplx)
                gradient_mag = np.array([A0 * ((A0**2+B0**2) ** (-1/2)), B0 * ((A0**2+B0**2) ** (-1/2))]) #some derivatives
                hessian_mag = np.array([[-((A0**2)*(A0**2+B0**2)**(-3/2))+(A0**2+B0**2)**(-1/2), -A0*B0*(A0**2+B0**2)**(-3/2)],
                                    [-A0*B0*(A0**2+B0**2)**(-3/2), -((B0**2)*(A0**2+B0**2)**(-3/2))+((A0**2+B0**2)**(-1/2))]])

                #quadratic terms
                H[2*(nnode)*ph + 2*k2][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] = -load_val * (beta_Z + (0.5 * beta_I* hessian_mag[0][0])) #a**2
                H[2*(nnode)*ph + 2*k2 + 1][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = -load_val * (beta_Z + (0.5 * beta_I * hessian_mag[1][1])) #b**2
                H[2*(nnode)*ph + 2*k2][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = -load_val * beta_I * hessian_mag[0][1] #cross quad. terms in taylor exp
                H[2*(nnode)*ph + 2*k2 + 1][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] =  -load_val * beta_I * hessian_mag[0][1]

                for i in range(len(out_lines)): #fill in H for the inlines
                    dss.Lines.Name(out_lines[i])
                    line_idx = get_line_idx(out_lines[i])

                    if cplx == 0: #real residual
                        #A_m and C_lm
                        H[2*(nnode)*ph + 2*k2][2*3*(nnode) + 2*ph*nline + 2*line_idx][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        #B_m and D_lm
                        H[2*(nnode)*ph + 2*k2 + 1][2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                    if cplx == 1: #complex residual
                        #A_m, D_lm
                        H[2*(nnode)*ph + 2*k2][2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        #B_m and C_lm
                        H[2*(nnode)*ph + 2*k2 + 1][2*3*(nnode) + 2*ph*nline + 2*line_idx][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = 1/2

                for j in range(len(in_lines)): #fill in H for the outlines
                    dss.Lines.Name(in_lines[j])
                    line_idx = get_line_idx(in_lines[j])

                    if cplx == 0:
                        #A_m and C_mn
                        H[2*(nnode)*ph + 2*k2][2*3*(nnode) + 2*ph*nline + 2*line_idx][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        #B_m and D_mn
                        H[2*(nnode)*ph + 2*k2 + 1][2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                    if cplx == 1:
                        #A_m and D_mn
                        H[2*(nnode)*ph + 2*k2][2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx + 1][2*(nnode)*ph + 2*k2][2*ph*(nnode-1) + (k2-1)*2] = 1/2
                        #C_m and B_mn
                        H[2*(nnode)*ph + 2*k2 + 1][2*3*(nnode) + 2*ph*nline + 2*line_idx][2*ph*(nnode-1) + (k2-1)*2] = -1/2
                        H[2*3*(nnode) + 2*ph*nline + 2*line_idx][2*(nnode)*ph + 2*k2 + 1][2*ph*(nnode-1) + (k2-1)*2] = -1/2

    #Linear Term
    for ph in range(0,3):
        if ph == 0: #set nominal voltage based on phase
            A0 = 1
            B0 = 0
        elif ph == 1:
            A0 = -1/2
            B0 = -1 * np.sqrt(3)/2
        elif ph == 2:
            A0 = -1/2
            B0 = np.sqrt(3)/2
        # for k3 in range(len(dss.Lines.AllNames())):
        for k2 in range(1, len(dss.Circuit.AllBusNames())):
            for cplx in range(0,2):
                load_val = d_factor(dss.Circuit.AllBusNames()[k2], cplx)

                #linear terms
                g_temp = np.zeros(len(X))
                g_temp[2*ph*nnode+ 2 * k2] = -load_val* beta_I * ((1/2 * (-2 * A0 * hessian_mag[0][0] - 2 * B0 * hessian_mag[0][1])) \
                                       +  gradient_mag[0])
                g_temp[2*ph*nnode+ 2 * k2 + 1] = -load_val * beta_I * ((1/2 * (-2* A0 *hessian_mag[0][1] - 2 * B0 * hessian_mag[1][1])) \
                                           +  gradient_mag[1])
                g[0,:,2*(nnode-1)*ph + 2*(k2-1) + cplx] = g_temp

                #constant terms
                b_factor = 0
                Sk = dss.CktElement.Powers() #retrieve powers
                if cplx == 1:
                    b_factor = dss.Capacitors.kvar() - Sk[1] #depends on if it's real or im residual
                    b_factor = 0
                elif cplx == 0:
                    b_factor = - Sk[0]
                    b_factor = 0

                b_temp = -load_val * (beta_S \
                    + (beta_I) * (hessian_mag[0][1] * A0 * B0 + (1/2)*hessian_mag[0][0] * A0**2 + (1/2)*hessian_mag[1][1] * B0**2) \
                    - beta_I * (A0 * gradient_mag[0] +B0* gradient_mag[1]) \
                    + beta_I * (A0**2 + B0**2) ** (1/2)) \
                    + b_factor #calculate out the constant term in the residual
                b[0][0][2*(nnode-1)*ph + 2*(k2-1) + cplx] = b_temp #store the in the b matrix

    Y = X.reshape(-1, 1)
    # enlarged_X = np.zeros((2*3*(nline+nnode), 1, 2*3*(nnode-1)))
    # X_T= np.zeros((1, 2*3*(nline+nnode), 2*3*(nnode-1)))
    # for n in range(2*3*nline):
    #     enlarged_X[:, :, n] = Y
    #     X_T[:, :, n] = Y.T

    FTKCL = np.zeros((2*3*(nnode-1), 1))

    for i in range(2*3*(nnode-1)):
        r = (Y.T @ (H[:, :, i] @ Y)) \
        + (g[0,:,i] @ Y) \
        + b[0,0,i]
        FTKCL[i,:] = r

#FT should be (2*3*1 + 2*3*nline + 2*3*(nnode-1)) x 1, and
#JT should be (2*3*1 + 2*3*nline + 2*3*(nnode-1)) x (2*3*nnode + 2*3*nline)
    print(FTKCL)
    print(FTKVL)
    print(FTSUBV)
    FT = np.r_[FTSUBV, FTKVL, FTKCL]
    return FT, g_SB, G_KVL, H, Y, g
    # return FT, g_SB, G_KVL, H, X_T, g