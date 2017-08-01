
import pandas as pd
import numpy as np
import datetime


# Import data from .csv
file_name = input("Enter the path/filename of .csv: ")
print("Your excel file will be saved in the same folder with your .csv as 'filename_analyzed.xlsx'")
df_raw = pd.read_csv(file_name)


# Trim to 24 hour range
lower_limit = datetime.time(10,0,0)
upper_limit = datetime.time(10,5,0)
def get_data_range(L, lower_limit, upper_limit):
    """
    Find the start and end indices for a 24 hour range starting between a given time range
    Takes arguments L - a list of datetime.time objects, lower_limit and upper_limit - datetime.time objects 
    to specificy the range in which to choose the start time
    Returns a tuple: (start_index, end_index)
    """
    start_index = 0
    for i in range(len(L)):
        if L[i] >= lower_limit and L[i] < upper_limit:
            start_index = i
            break
    return (start_index, start_index + 288)


# Trim raw data to 24 hour window
df_raw.Time = pd.to_datetime(df_raw.Time, format='%H:%M:%S').dt.time
trim_index = get_data_range(list(df_raw.Time), lower_limit, upper_limit)
df = df_raw[trim_index[0]:trim_index[1]]
df = df.reset_index(drop=True)

trimmed_copy_df = df.copy() # to be used in final output to excel 

# Make a column of bools to indicate day vs night

night_start = datetime.time(22,0,0)
night_end = datetime.time(10,0,0)
def isNight(x, night_start, night_end):
    """
    Take datetime.time object and return True if between 10pm and 10am, False otherwise 
    """
    if (x >= night_start and x < datetime.time(23, 59, 59)) or x < night_end:
        return True
    else:
        return False

# Create Boolean column indicating Night=True Day=False
# use df.isNight = df.Time.apply(isNight) if day/night not split between bottom/top
df.isNight = pd.Series([x > len(df)/2-1 for x in range(len(df))]) 

# Generate bout indices
def get_bout_indices(L):
    """
    Takes a list L and returns a list of tuples of the start/end indices in which sleeping bouts occurred.
    I.e. if two sleeping bouts occured, the first from index 5 to 20, and the second from index 30 to 40,
    this function will return [(5,20), (30,40)]
    """
    indices = []
    start_index = 1
    end_index = 1
    in_bout = False
    
    for i in range(len(L)):
        if L[i] == 0 and in_bout == False: 
            start_index = i
            in_bout = True
        if (L[i] != 0 or i == len(L)-1) and in_bout == True:
            end_index = i
            in_bout = False
            if i == len(L)-1:
                indices.append((start_index, end_index+1))
            else:
                indices.append((start_index, end_index))
    return indices 


def create_sleeping_columns(df):
    """
    Creates a new boolean column for each fly. True indicates fly is asleep for that window.
    Columns used for filters in data analysis. 
    """
    for i in range(5):
        df.loc[:,'fly' + str(i+1) + 'sleeping'] = df.iloc[:,i+11].apply(lambda x: x == 0)

create_sleeping_columns(df)

# Get day bouts and night bouts
# Redundancy/messy here - refactor
colnames = df.columns[11:16] # Ordered list of fly genotypes
def get_day_night_bouts(df, resp_colnum, sleep_colnum):
    """
    Takes a dataframe, the colnumn number for resp data, column number for sleep data
    Returns a tuple of two lists of lists: resp data for daytime sleep bouts, resp data for nighttime sleep bouts
    """
    bout_indices = get_bout_indices(list(df.iloc[:,sleep_colnum]))
    resp_bouts_day = []
    resp_bouts_night = []
    for i in bout_indices:
        if df.isNight[i[0]:i[1]].mean() >= 0.5:
            resp_bouts_night.append(list(df.iloc[:,resp_colnum])[i[0]:i[1]])
        else:
            resp_bouts_day.append(list(df.iloc[:,resp_colnum])[i[0]:i[1]])
    if not resp_bouts_day:
        resp_bouts_day = ['none']
    if not resp_bouts_night:
        resp_bouts_night = ['none']
    return resp_bouts_day, resp_bouts_night

def get_all_bouts(df, colnames):
    """
    Returns a tuple of two dictionaries - individual bouts for each fly for 1) day sleep, 2) night sleep
    Dictionaries format - key: genotype; value: list of lists containing mr for individual sleeping bouts
    """
    resp_colnum = 4
    sleep_colnum = 11
    colnames = df.columns[11:16]
    all_day_bouts = {x: [] for x in colnames}
    all_night_bouts = {x: [] for x in colnames}
    for i in range(5):
        day_bouts, night_bouts = get_day_night_bouts(df, resp_colnum, sleep_colnum)
        all_day_bouts[df.columns[i+11]] += day_bouts 
        all_night_bouts[df.columns[i+11]] += night_bouts 
        resp_colnum+=1
        sleep_colnum+=1
    return all_day_bouts, all_night_bouts

day_bouts_dict, night_bouts_dict = get_all_bouts(df, colnames)


def get_all_bouts_list(day_bouts_dict, night_bouts_dict, colnames):
    all_bouts_day_list = []
    all_bouts_night_list = []
    for i in colnames:
        all_bouts_day_list += day_bouts_dict[i] + [[]] # empty lists between columns indicate different flies
        all_bouts_night_list += night_bouts_dict[i] + [[]]
    return all_bouts_day_list, all_bouts_night_list

all_bouts_day_list, all_bouts_night_list = get_all_bouts_list(day_bouts_dict, night_bouts_dict, colnames)

# Create dataframes for day/night bouts
all_day_bouts_df = pd.DataFrame(all_bouts_day_list).transpose()
all_night_bouts_df = pd.DataFrame(all_bouts_night_list).transpose()

# Get sleep profiles
def get_sleep_profile(df, resp_colnum, sleep_colnum):
    """
    Returns a list of tuples with sum of metabolic rate and the percentage sleep and total beam breaks for each hour in the 24 hour window
    """
    fly1_sleep = df.iloc[:,sleep_colnum]
    fly1_resp = df.iloc[:,resp_colnum]
    hourly_resp_sleep = []
    for i in range(24):
        sleep = fly1_sleep[i*12:i*12+12]
        resp = fly1_resp[i*12:i*12+12]
        num_sleep_blocks = 0
        for i in sleep:
            if i == 0:
                num_sleep_blocks += 1
        sleep_avg = num_sleep_blocks / 12 * 100
        hourly_resp_sleep.append((resp.sum(), sleep_avg, sleep.sum()))
    return hourly_resp_sleep

def make_sleep_profile_dict(df):
    """
    Returns a dictionary containing a time index and the sleep profiles (both metabolic rate sum and average sleep)
    for each fly in the dataframe
    """
    resp_colnum = 4
    sleep_colnum = 11
    sleep_profile_dict = {}
    sleep_profile_dict['Time'] = [df.Time[x*12-1] for x in range(1, 25)]
    for i in range(5):
        sleep_profile = get_sleep_profile(df, resp_colnum, sleep_colnum)
        sleep_profile_dict[df.columns[sleep_colnum] + ' MR Sum'] = [x[0] for x in sleep_profile] #name of genotype is header of sleep column
        sleep_profile_dict[df.columns[sleep_colnum] + ' Avg Sleep'] = [x[1] for x in sleep_profile]
        sleep_profile_dict[df.columns[sleep_colnum] + ' Beam Breaks'] = [x[2] for x in sleep_profile]
        resp_colnum+=1
        sleep_colnum+=1
    return sleep_profile_dict

def make_sleep_profile_colnames(df):
    """
    Create list of ordered column names for dataframe to be created from sleep_profile dictionary
    """
    colnames = ['Time']
    for i in range(11,16):
        colnames.append(df.columns[i] + ' MR Sum')
        colnames.append(df.columns[i] + ' Avg Sleep')
        colnames.append(df.columns[i] + ' Beam Breaks')
    return colnames

sleep_profile_dict = make_sleep_profile_dict(df)
sleep_profile_df = pd.DataFrame(sleep_profile_dict, columns=make_sleep_profile_colnames(df))


#Total Sleep
def get_sleep_minutes_df(df, colnames):
    total_sleep_list = [[x, ] for x in colnames]
    for i in range(len(colnames)):
        total_sleep_list[i].append(df.iloc[:,i+16].sum()*5)
        total_sleep_list[i].append(df.iloc[:,i+16][df.isNight == False].sum()*5)
        total_sleep_list[i].append(df.iloc[:,i+16][df.isNight == True].sum()*5)
    return pd.DataFrame(total_sleep_list, columns=['Fly', 'Total Sleep Min',
                                                   'Total Day Sleep Min', 'Total Night Sleep Min'])

sleep_minutes_df = get_sleep_minutes_df(df, colnames)


# Wake Sleep MR
def get_wake_sleep_mr_df(df, colnames):
    wake_sleep_mr_list = [[x, ] for x in colnames]
    for i in range(len(colnames)):
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.iloc[:,i+16] == False].mean())
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.iloc[:,i+16] == True].mean())
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.isNight == False].mean())
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.isNight == True].mean())
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.iloc[:,i+16] == True][df.isNight == False].mean())
        wake_sleep_mr_list[i].append(df.iloc[:,i+4][df.iloc[:,i+16] == True][df.isNight == True].mean())
    return pd.DataFrame(wake_sleep_mr_list, columns=['Fly', 'Mean Wake MR', 'Mean Sleep MR', 'Mean Day MR', 
                                                     'Mean Night MR', 'Mean Day Sleep MR', 'Mean Night Sleep MR'])

wake_sleep_mr_df = get_wake_sleep_mr_df(df, colnames)


# Mean Hourly Sleep MR
def get_mean_hourly_sleep_mr_df(df, sleep_profile_df, colnames):
    mr_hourly = sleep_profile_df.iloc[:,1::3]
    mr_hourly.isNight = pd.Series([x > len(mr_hourly)/2-1 for x in range(len(mr_hourly))]) 
    mean_hourly_list = [[x, ] for x in colnames]
    for i in range(len(colnames)):
        mean_hourly_list[i].append(mr_hourly.iloc[:,i].mean())
        mean_hourly_list[i].append(mr_hourly.iloc[:,i][mr_hourly.isNight == False].mean())
        mean_hourly_list[i].append(mr_hourly.iloc[:,i][mr_hourly.isNight == True].mean())
    return pd.DataFrame(mean_hourly_list, columns=['Fly', 'Mean Hourly MR Total', 'Mean Hourly MR Day', 
                                                   'Mean Hourly MR Night'])

mean_hourly_sleep_mr_df = get_mean_hourly_sleep_mr_df(df, sleep_profile_df, colnames)


# Export to .xlsx

# Convert datetime.time columns back to str for correct formatting in Excel
sleep_profile_df.Time = sleep_profile_df.Time.apply(lambda x: str(x))
trimmed_copy_df.Time = trimmed_copy_df.Time.apply(lambda x: str(x)) 

writer = pd.ExcelWriter(file_name[:-4] + '_analyzed.xlsx', engine='xlsxwriter')

trimmed_copy_df.to_excel(writer, sheet_name='Trimmed Analysis', index = False)
all_day_bouts_df.to_excel(writer, sheet_name='All Day Bouts', index = False, header = False)
all_night_bouts_df.to_excel(writer, sheet_name='All Night Bouts', index = False, header = False)
sleep_profile_df.to_excel(writer, sheet_name='Sleep Profile', index = False)
sleep_minutes_df.to_excel(writer, sheet_name='Min. of Sleep', index = False)
wake_sleep_mr_df.to_excel(writer, sheet_name='Wake Sleep MR', index = False)
mean_hourly_sleep_mr_df.to_excel(writer, sheet_name='Mean Hourly Sleep', index = False)

writer.save()

print("Process finished.")
