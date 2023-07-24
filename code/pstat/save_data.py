import numpy as np

class Test:
    '''
    '''
    def __init__(self):
        print('Test from save_data module')



class Save:
    '''
    '''
    def __init__(self, data, fileName, header, technique):
        self.fileName = fileName
        self.data_array = 0
        if technique == 'CV' :
            header = header + '\nt/s, Vf/V, Im/A, Vsig/V\n' 
            self.data_array = CV(fileName, data).save()
        elif technique == 'CA':
            header = header + '\nt/s, Vf/V, Im/A, Vsig/V\n'
            self.data_array = CA(fileName, data).save()
        elif technique == 'OCP':
            header = header + '\nt/s, Vf/V, Vsig/V\n'
            self.data_array = OCP(fileName, data).save()
        np.savetxt(fileName, self.data_array, delimiter=',', header=header)


class CA:
    '''
    '''
    def __init__(self, fileName, data):
        self.fileName = fileName
        self.data = data
        data_array = 0

    def save(self):
        
        t = mscript.get_values_by_column(self.data,0)
        Vf = mscript.get_values_by_column(self.data,1)
        Im = mscript.get_values_by_column(self.data,3)
        Vsig = mscript.get_values_by_column(self.data,5)
        data_array = np.array([t,Vf,Im,Vsig]).T

        return data_array


class OCP:
    '''
    '''
    def __init__(self, fileName, data):
        self.fileName = fileName
        self.data = data
        data_array = 0

    def save(self):
        t = mscript.get_values_by_column(self.data,0)
        Vf = mscript.get_values_by_column(self.data,1)
        Vsig = mscript.get_values_by_column(self.data,3)
        data_array = np.array([t,Vf,Vsig]).T
        
        return data_array
    
class CV:
    '''
    '''
    def __init__(self, fileName, data):
        self.fileName = fileName
        self.data = data
        data_array = 0

    def save(self):
        
        t = mscript.get_values_by_column(self.data,0)
        Vf = mscript.get_values_by_column(self.data,1)
        Im = mscript.get_values_by_column(self.data,3)
        Vsig = mscript.get_values_by_column(self.data,4)
        Cy = mscript.get_values_by_column(self.data,9)
        data_array = np.array([t,Vf,Im,Vsig,Cy]).T

        return data_array


