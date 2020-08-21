# System dependencies
from os import listdir
import time as clock
from datetime import timedelta
from IPython.display import clear_output

import pickle
import gzip
import re

# Data manipulation dependencies
import pandas as pd
import numpy as np
import datetime as dt

### Prep Cleaning

def get_time( spec=None ):
    if type(spec) is str:
        spec = float( spec )
    
    return clock.strftime("%Y-%m-%dT%H:%M:%S", clock.localtime( spec ))

def get_stamp( spec ):
    try:
        sf = "%Y-%m-%dT%H:%M:%S"
        return int(clock.mktime( clock.strptime( spec, sf ) ))
    except:
        try:
            sf = "'%Y-%m-%dT%H:%M:%S'"
            return int(clock.mktime( clock.strptime( spec, sf ) ))
        except:
            return 0

def check_static( alist ):
    return alist[1:] == alist[:-1]

def check_header( line ):
    if line.find(" ") < 0:
        try:
            return line[0] == '%'
        except:
            return False
        
    else:
        chunks = line.split(" ")
        try:
            return (chunks[0][0] == '%') or ( chunks[2].find("comet") >= 0 )
        except:
            return False

#def group_from_txt(  ):
#    

def check_job( chunk ):
    return chunk.find("-") == -1

def open_txt( txt_file ):
    
    with open( txt_file, "rt" ) as f:
        lines = f.readlines()
        f.close()
    
    return lines

def unzip_txt( gzipped ):
    
    with gzip.open( gzipped, 'rt') as f:
        lines = f.readlines()
        f.close()
    
    return lines

def group_from_txt( txt_file ):
    lines = open_txt( txt_file )
    group = []
    
    for line in lines:
        chunks = line.split(" ")
        nodelist_r = chunks[0]
        nodelist = format_nodelist( chunks[0] )
        start = get_stamp( chunks[1] )
        end = get_stamp( chunks[2] )
        
        item = ( nodelist, start, end )
        group.append(item)
        
    return group

def quick_save( obj, label=get_time() ):
    
    try:
        out_file = open( label, 'wb')
        pickle.dump( obj, out_file)
        
        # double check save
        check_cpicore_set = pickle.load(open(cpiset_out, 'rb'))
        check_cpicore_set = None
        
    except:
        "There was a problem pickling the object - Save manually."

####Data Munging

def info_dict( rules, info ):
    rules_list = rules.split("|")
    
    if len(rules_list) != len(info):
        return {}
    
    else:
        return { rules_list[i]:info[i] for i in range(len(rules_list)) }

def host_to_info_dict( zip_txt ):
    contents = unzip_txt( zip_txt )
    host_name = contents[1].partition(" ")[2][:11]
    out_dict = { host_name: {} }
    host_info = {}
    info_dict = { "Data":{},
                    "Job":"N/A",
                    "Schemas":{},
                    "Specs":[]
                }
    
    for line in contents:
            
        if line[0] == "$":
            info_dict["Specs"].append( format_spec( line ) )
            
        elif line[0] == "!":
            info_dict["Schemas"].update( format_schema( line ) )
        
        else:
            
            if (len(line) > 0) and (len(line) < 3 or check_header( line )):
                header_dict = format_header( line )
                
                if header_dict:
                    t = header_dict["Timestamp"]
                    host_info[ t ] = {}
                    
                    if check_job( header_dict["Jobid"] ):
                        info_dict["Job"] = { "Jobid": header_dict["Jobid"] } 
                    
            else:
                incoming = format_data( line )
                info_dict["Data"].update(incoming)
                
                host_info[t].update( info_dict )
                
    out_dict[host_name].update( host_info )
    
    return out_dict

def job_to_info_dict( txt_file_list ):
    nodes_by_date = {}
    unsaved = []

    for date in txt_file_list:
        try:
            # skip alt files
            #check_stamp = int( date[-14] )
            
            # read in file contents
            contents = open_txt( date )
            
            # formatting
            label = date[-14:-4]
            rules = contents[0]
            jobs = contents[1:]
            
            # template to save
            nodes_by_date[ label ] = {}
            nodes_by_date[ label ]["multiple"] = {}
            nodes_by_date[ label ]["rules"] = rules
            
            # run through lines in file
            for job in jobs:
                line = job.split("|")
                node = line[-1]
                info = info_dict( rules, line )
                
                # save multiple node jobs to specified loc
                if len(node) > 12:
                    nodes = format_nodelist( info )
                    for node in nodes:
                        nodes_by_date[ label ][ "multiple" ][ node ] = info
                
                else:
                    nodes_by_date[ label ][ node[:11] ] = info
        except:
            unsaved.append(date)
            
    
    return nodes_by_date, unsaved

####Formatting

def format_header( line ):
    chunks = line.split(" ")
    
    try:
        if chunks[0][0] == '%':
            return {}
        else:
            return { "Timestamp": get_time( chunks[0] ), 
                     "Jobid": chunks[1],
                     "Host": chunks[2][:11] }
        
    except:
        return {}

def format_nodelist( nodelist ):
    purged = nodelist.replace('[','').replace(']','').replace(',','-').replace('-','').split("comet")[1:]
    nodes = []
    
    for item in purged:
        base = item[:2]
        prev = 2
        
        for i in range( 4,len(item)+1,2 ):
            node = 'comet' + '-' + base + '-' + item[ prev:i ]
            nodes.append(node)
            prev = i
    return nodes

def format_spec( line ):
    return line[1:-1]

def format_data( line ):
    chunks = line.split(" ")
    
    stat = chunks[0]
    dev = chunks[1]
    data = chunks[2:-1]
    
    return { (stat,dev): data }

def format_schema( line ):
    chunks = line.partition(" ")
    stat = chunks[0][1:]
    
    temp_sch = chunks[2:][0][:-1].replace(",E","").replace(",C","").split(" ")
    fin_sch = []
    
    for item in temp_sch:
        
        if item.find("=") > -1:
            new = item.replace(",","(") + ")"
            fin_sch.append( new )
        
        else:
            fin_sch.append( item )
    
    return { stat:fin_sch }

def separate_nodes( search_tup ):
    nl = search_tup[0]
    t_0 = search_tup[1]
    t_n = search_tup[2]
    exp_list = []
    
    if len( search_tup ) > 3:
        rem = search_tup[3:]
    
    for node in nl:
        if len(search_tup) > 3:
            exp_list.append( (node,t_0,t_n,rem) )
        else:
            exp_list.append( (node,t_0,t_n) )
    
    return exp_list
    
def from_list( chunks ):
    nl_i = chunks.index("comet")
    nl = chunks[ nl_i ]
    t_n = ''
    
    if nl_i == 0:
        t_0 = chunks[1]
    else:
        t_0 = chunks[0]
    
    try:
        for i in range(len(chunks)):
            if chunks[ i ] < t_0:
                t_0 = chunks[ i ]
            elif chunks[ i ] > t_0 and (t_n == '' or t_n < chunks[ i ]):
                t_n = chunks[ i ]                          
    except:
        next
    
    if len(chunks) > 3:
        rem = [ e for e in chunks if (e is not nl) and (e not in ts) ]
        return nl,ts,rem
    else:
        return nl,ts
    return (nl, t_0, t_n)

def from_tup( list_i ):
    nl = ''
    ts = []

    for e in list_i:
        if 'comet' in e:
            nl = e
        if 'T' in e:
            try:
                if get_stamp(e) is not '0':
                    ts.append(t)
            except:
                next
    
    if len(list_i) > 3:
        rem = [ e for e in list_i if (e is not nl) and (e not in ts) ]
        return nl,sorted(ts),rem
    else:
        return nl,sorted(ts)

def sort_input( aline ):
    if type( aline ) is list:
        return from_list(aline)
    if type( aline ) is tuple:
        return from_tup(aline)
    
def format_search_tup( line ):
    
    if len(line) > 1:
        search_i = sort_input( line )
        
        nodelist = format_nodelist( search_i[0] )
        start = get_stamp( search_i[1] )
        end = get_stamp( search_i[2] )
        
        if len(search_i) > 3:
            return nodelist,start,end,search_i[3:]
        else:
            return nodelist,start,end
    else:
        return 1

####Data analysis

def timely_dict( host_data, host_name ):
    stamps = list(host_data[ host_name ].keys())
    schemas = host_data[ host_name ][ stamps[0] ]["Schemas"]
    timely_data = []
    
    for stamp in stamps:
        for key,data in host_data[ host_name ][ stamp ]["Data"].items():
            
            stat = key[0]
            dev = key[1]
            
            for i in range(len(data)):
                metric = schemas[stat][i]
            
            info = (stat, metric, dev, int(data[i]), stamp)
            timely_data.append( info )
    
    return timely_data

# PARAMETERS:
# 's/e' single search from start/end (manual)
#       ie) "Start, End: 2020-01-03T20:34:47, 2020-01-05T08:15:18"
# 's' single search from nodelist%start%end (manual)
#       ie) "NL, Start, End: comet-05-12 2020-03-03T20:34:47 2020-03-05T08:15:18"
#       ie) "NL, Start, End: comet-05-[12,16] 2020-03-03T20:34:47 2020-03-05T08:15:18"
# 'l' repeated search from nodelist%start%end strings or (nodelist,start,end) tuples (from list)
#       ie) myJobList = [ "comet-05-12 2020-03-03T20:34:47 2020-03-05T08:15:18",
#                          (comet-05-12, 2020-03-03T20:34:47, 2020-03-05T08:15:18)   ]
#           search( mode='l', myJobList )
# 'f' repeated search from nodelist%start%end (from file)
#       ie) "Text file: your_search_file.txt"  (Note: Mismatched file contents ignored)
def search( mode=['s/e', 's', 'l','f'], from_list=False ):
    
    if mode == 's/e':
        t_0,t_n = input("Start, End:").replace(",", "").split(" ")
        start = get_stamp( t_0 )
        end=get_stamp( t_n )
        return start,end
    
    elif mode == 's':
        line = input("NL, Start, End:").replace(",", "").split(" ")
        line_tup = format_search_tup( line )
        return line_tup

    elif mode == 'l' and type(from_list) is list:
        try:
            out_list = []
            dropped = []
            
            for item in from_list:
                try:
                    item_tup = format_search_tup( item )
                    if len(item_tup[0] == 1):
                        out_list.append( item_tup )
                    else:
                        expanded_tups = separate_nodes(item_tup)
                        out_list = out_list + expanded_tups
                except:
                    dropped.append(item)
            return out_list,dropped
        except:
            "Unable to process variable passed to function. All items in list should be in"
    
    elif mode == 'f':
        search_list = group_from_text( input("Text file:") )
        return search_list
    
    else:
        return 1