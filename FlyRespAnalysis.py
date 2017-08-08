
# coding: utf-8

# ### Import Libraries that will be needed

# In[1]:

import pandas as pd
import datetime


# ### Import data from .csv and reformat time

# In[2]:

df_raw = pd.read_csv("Sample_Data.csv")

#Convert Time column to datetime.time format
df_raw.Time = pd.to_datetime(df_raw.Time, format='%H:%M:%S').dt.time 


# ### Trim to 24 hour range

# In[3]:

def get_data_range(time_list):
    """
    Find the start and end indices for a 24 hour range starting between 
    10:00am and 10:05am.
    Takes time_list - a list of datetime.time objects
    Returns a tuple: (start_index, end_index)
    *Selects first encountered instance of time between 
    10:00am and 10:05am as start index*
    """
    lower_limit = datetime.time(10,0,0)
    upper_limit = datetime.time(10,5,0)
    start_index = 0
    
    for i in range(len(time_list)):
        if time_list[i] >= lower_limit and time_list[i] < upper_limit:
            start_index = i
            break
            
    #288 is the number of rows until 24 hours later
    return (start_index, start_index + 288) 


# In[4]:

# Trim raw data to 24 hour window
trim_start, trim_end = get_data_range(list(df_raw.Time))
df = df_raw[trim_start:trim_end]
df = df.reset_index(drop=True)
df_trimmed_copy = df.copy() # to be used in final output to excel 


# ### Create reference columns

# In[5]:

# Create Boolean column indicating Night=True Day=False
# In most cases this should be just split into top/bottom half of df;
# implented as a function in case assumption is not met.
def is_night(x):
    """
    Take datetime.time object and return True if between 10pm and 10am;
    return False otherwise.
    """
    night_start = datetime.time(22,0,0)
    night_end = datetime.time(10,0,0)
    if (x >= night_start and x < datetime.time(23, 59, 59)) or x < night_end:
        return True
    else:
        return False


# In[6]:

df.isNight = df.Time.apply(is_night)


# In[7]:

# Create boolean columns for fly sleeping state
def create_sleeping_columns(df):
    """
    Creates a new boolean column for each fly. True indicates fly is asleep 
    (activity = 0) for that time point.
    Columns used for filters in data analysis. 
    """
    act_col = 11
    
    for i in range(5):
        df.loc[:,'fly' + str(i+1) + 'sleeping'] = df.iloc[:,i+act_col].apply(lambda x: x == 0)


# In[8]:

create_sleeping_columns(df)


# ### Get day and night bouts and create dataframes

# In[9]:

# Following code creates two new dataframes: all_day_bouts_df, all_night_bouts_df
# These will be exported to two different sheets in excel. 

def get_bout_indices(activity_list):
    """
    Takes a list, activity_list, and returns a list of tuples of 
    the start/end indices in which sleeping bouts occurr.
    I.e. if two sleeping bouts occured, the first from index 5 to 20,
    and the second from index 30 to 40, this function will return 
    [(5,20), (30,40)]
    """
    indices = []
    start_index = 1
    end_index = 1
    in_bout = False
    
    for i in range(len(activity_list)):
        if activity_list[i] == 0 and in_bout == False: 
            start_index = i
            in_bout = True
        if (activity_list[i] != 0 or i == len(activity_list)-1) and in_bout == True:
            end_index = i
            in_bout = False
            if i == len(activity_list)-1:
                indices.append((start_index, end_index+1))
            else:
                indices.append((start_index, end_index))
                
    return indices 


# In[10]:

colnames = df.columns[11:16] # Ordered list of fly genotype name strings

def get_day_night_bouts(df, resp_colnum, activity_colnum):
    """
    Gets lists of mr rates for a single fly during during indepedent sleeping 
    bouts during either day or night. 
    Takes dataframe, column number for resp data, column number for sleep data.
    Returns a tuple of two lists of lists: resp data for daytime sleep bouts, 
    and resp data for nighttime sleep bouts
    """
    bout_indices = get_bout_indices(list(df.iloc[:,activity_colnum]))
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
    Returns a tuple of two dictionaries containing individual bouts for each fly 
    for 1) day sleep, 2) night sleep
    Dictionary format - key: genotype; value: list of lists containing mr data
    for individual sleeping bouts
    """
    mr_col = 4
    act_col = 11
    static_act_col = 11
    colnames = df.columns[11:16]
    all_day_bouts = {x: [] for x in colnames}
    all_night_bouts = {x: [] for x in colnames}
    
    for i in range(5):
        day_bouts, night_bouts = get_day_night_bouts(df, mr_col, act_col)
        all_day_bouts[df.columns[i+static_act_col]] += day_bouts 
        all_night_bouts[df.columns[i+static_act_col]] += night_bouts 
        mr_col+=1
        act_col+=1
        
    return all_day_bouts, all_night_bouts


# In[11]:

day_bouts_dict, night_bouts_dict = get_all_bouts(df, colnames)


# In[12]:

def get_all_bouts_df(day_bouts_dict, night_bouts_dict, colnames):
    """
    Takes dictionaries day_bouts_dict and night_bouts_dict and returns 
    a tuple of two dataframes containing the information in the dictionaries 
    properly formatted for excel output.
    Different flies are seperated by an empty column. 
    """
    all_bouts_day_list = []
    all_bouts_night_list = []
    
    for i in colnames:
        # [[]] used to create empty lists between columns to indicate different flies
        all_bouts_day_list += day_bouts_dict[i] + [[]] 
        all_bouts_night_list += night_bouts_dict[i] + [[]]
        
    all_day_df = pd.DataFrame(all_bouts_day_list).transpose()
    all_night_df = pd.DataFrame(all_bouts_night_list).transpose()
    
    return all_day_df, all_night_df


# In[13]:

# Create dataframes for day/night bouts
all_day_bouts_df, all_night_bouts_df = get_all_bouts_df(day_bouts_dict, night_bouts_dict, colnames)


# In[14]:

all_day_bouts_df


# ### Get sleep profiles and create dataframe

# In[15]:

# Following code is used to create the sleep_profile dataframe, 
# which will be exported as it's own sheet in the excel output. 
def get_single_sleep_profile(df, resp_colnum, activity_colnum):
    """
    Returns a list of tuples with metabolic rate sums, the percentage sleep, 
    and total beam breaks per hour for 24 hours, for one individual fly.
    """
    fly_activity = df.iloc[:,activity_colnum]
    fly_resp = df.iloc[:,resp_colnum]
    hourly_resp_sleep = []
    
    for i in range(24):
        #12 rows are selected at a time to bin into 1-hour 
        activity = fly_activity[i*12:i*12+12] 
        resp = fly_resp[i*12:i*12+12]
        num_sleep_blocks = 0
        for i in activity:
            if i == 0:
                num_sleep_blocks += 1
        sleep_avg = num_sleep_blocks / 12 * 100
        hourly_resp_sleep.append((resp.sum(), sleep_avg, activity.sum()))
        
    return hourly_resp_sleep

def make_sleep_profile_colnames(df):
    """
    Create list of ordered column names for dataframe to be created 
    from sleep_profile dictionary
    """
    colnames = ['Time']
    
    for i in range(11,16):
        colnames.append(df.columns[i] + ' MR Sum')
        colnames.append(df.columns[i] + ' Avg Sleep')
        colnames.append(df.columns[i] + ' Beam Breaks')
        
    return colnames

def make_sleep_profile_df(df):
    """
    Returns a dictionary containing a time index and the sleep profiles 
    (both metabolic rate sum and average sleep) for each fly in the dataframe.
    """
    mr_col = 4
    act_col = 11
    sleep_profile_dict = {}
    sleep_profile_dict['Time'] = [df.Time[x*12-1] for x in range(1, 25)]
    
    def add_to_dict(name, index):
        sleep_profile_dict[df.columns[act_col] + name] = [x[index] for x in sleep_profile]
        
    for i in range(5):
        sleep_profile = get_single_sleep_profile(df, mr_col, act_col)
        add_to_dict(' MR Sum', 0)
        add_to_dict(' Avg Sleep', 1)
        add_to_dict(' Beam Breaks', 2)
        mr_col+=1
        act_col+=1
        
    sleep_profile_all = pd.DataFrame(sleep_profile_dict, 
                                     columns=make_sleep_profile_colnames(df))
    
    return sleep_profile_all


# In[16]:

sleep_profile_df = make_sleep_profile_df(df)


# In[17]:

sleep_profile_df


# ### Create summary dataframes

# In[18]:

# Following code is used to analyze the data processed above, and generate 
# three dataframes, which will become three sheets in the final excel output. 

#Total Sleep 
def get_sleep_minutes_df(df, colnames):
    """
    Create summary df of minutes of sleep for each fly. 
    Exported as sheet to excel.
    """
    total_sleep_list = [[x, ] for x in colnames]
    sleep_col = 16
    column_names = ['Fly', 
                    'Total Sleep Min',
                    'Total Day Sleep Min', 
                    'Total Night Sleep Min']
    
    def add_to_list(data):
        total_sleep_list[i].append(data)
    
    for i in range(len(colnames)):
        sleep_ser = df.iloc[:,i+sleep_col]
        # data are in 5min bins, multiply by 5 to make per minute
        add_to_list(sleep_ser.sum()*5) 
        add_to_list(sleep_ser[df.isNight == False].sum()*5)
        add_to_list(sleep_ser[df.isNight == True].sum()*5)
        
    return pd.DataFrame(total_sleep_list, columns=column_names)


# In[19]:

sleep_minutes_df = get_sleep_minutes_df(df, colnames)


# In[20]:

sleep_minutes_df


# In[21]:

# Wake Sleep MR
def get_wake_sleep_mr_df(df, colnames):
    """
    Create summary df of average metabolic rates during selected 
    time periods for each fly. Exported as sheet to excel. 
    """
    wake_sleep_mr_list = [[x, ] for x in colnames]
    mr_col = 4
    sleep_col = 16
    column_names = ['Fly',
                    'Mean Wake MR',
                    'Mean Sleep MR',
                    'Mean Day MR', 
                    'Mean Night MR', 
                    'Mean Day Sleep MR',
                    'Mean Night Sleep MR']
    
    def add_to_list(data):
        wake_sleep_mr_list[i].append(data)
    
    for i in range(len(colnames)):
        mr_ser = df.iloc[:,i+mr_col]
        sleep_ser = df.iloc[:,i+sleep_col]
        
        add_to_list(mr_ser[sleep_ser == False].mean())
        add_to_list(mr_ser[sleep_ser == True].mean())
        add_to_list(mr_ser[df.isNight == False].mean())
        add_to_list(mr_ser[df.isNight == True].mean())
        add_to_list(mr_ser[sleep_ser == True][df.isNight == False].mean())
        add_to_list(mr_ser[sleep_ser == True][df.isNight == True].mean())            
        
    return pd.DataFrame(wake_sleep_mr_list, columns=column_names)


# In[22]:

wake_sleep_mr_df = get_wake_sleep_mr_df(df, colnames)


# In[23]:

wake_sleep_mr_df


# In[24]:

def get_mean_hourly_sleep_mr_df(sleep_profile, colnames):
    """
    Creates summary df for mean hourly sleeping metabolic rate for each fly. 
    Exported as sheet to excel. 
    """
    mr_hourly = sleep_profile.iloc[:,1::3]
    # sleep profile is split into top half: day; bottom half: night
    night_bool_list = [x > len(mr_hourly)/2-1 for x in range(len(mr_hourly))]
    mr_hourly.isNight = pd.Series(night_bool_list)      
    mean_hourly_list = [[x, ] for x in colnames]
    column_names = ['Fly', 
                    'Mean Hourly MR Total', 
                    'Mean Hourly MR Day', 
                    'Mean Hourly MR Night']
    
    def add_to_list(data):
        mean_hourly_list[i].append(data)
    
    for i in range(len(colnames)):
        mr_ser = mr_hourly.iloc[:,i]
        add_to_list(mr_ser.mean())
        add_to_list(mr_ser[mr_hourly.isNight == False].mean())
        add_to_list(mr_ser[mr_hourly.isNight == True].mean())
        
    return pd.DataFrame(mean_hourly_list, columns=column_names)


# In[25]:

mean_hourly_sleep_mr_df = get_mean_hourly_sleep_mr_df(sleep_profile_df, colnames)


# In[26]:

mean_hourly_sleep_mr_df


# ## Export to .xlsx

# In[27]:

# Convert datetime.time columns back to str for correct formatting in Excel
sleep_profile_df.Time = sleep_profile_df.Time.astype(str)
df_trimmed_copy.Time = df_trimmed_copy.Time.astype(str)

def excel_out(df, name, **kwargs):
    """
    Wrapper function - Takes a dataframe, and a desired sheet name (str).
    Sends to new sheet in excel output
    """
    df.to_excel(writer, sheet_name = name, index = False, **kwargs)
    
writer = pd.ExcelWriter('sample_out.xlsx', engine='xlsxwriter')
excel_out(df_trimmed_copy, 'Trimmed Analysis')
excel_out(all_day_bouts_df, 'All Day Bouts', header = False)
excel_out(all_night_bouts_df, 'All Night Bouts', header = False)
excel_out(sleep_profile_df, 'Sleep Profile')
excel_out(sleep_minutes_df, 'Min. of Sleep')
excel_out(wake_sleep_mr_df, 'Wake Sleep MR')
excel_out(mean_hourly_sleep_mr_df, 'Mean Hourly Sleep')
writer.save()

