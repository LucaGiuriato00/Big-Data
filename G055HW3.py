from pyspark import SparkContext, SparkConf
from pyspark.streaming import StreamingContext
from pyspark import StorageLevel
import threading
import sys
import numpy as np
import random

# After how many items should we stop?
n = -1 # To be set via command line


# Operations to perform after receiving an RDD 'batch' at time 'time'
def process_batch(time, batch):
    # We are working on the batch at time `time`.
    global streamLength, histogram, m_sample
    batch_size = batch.count()
    
    
    # If we already have enough points (>n), skip this batch.
    if streamLength[0]>=n:
        return
    m=np.ceil(1/phi)
    
    # Extract the batch items from the batch
    batch_items = batch.map(lambda s: (int(s), 1)).reduceByKey(lambda i1, i2: i1+i2).collectAsMap()
    batch_items_list = batch.map(lambda s: int(s)).collect()
    
    
    # Update the streaming state
    
    #Exact alg. part
    for key in batch_items:
        if key not in histogram:
            histogram[key] = batch_items[key]
        else:
            histogram[key] += batch_items[key]
            
    #Resevoir sample part        
    b_ind=0
    for batch in batch_items_list:
        b_ind+=1
        if (streamLength[0]+b_ind)<m:
            m_sample.append(batch)
        else:
            r=random.random()
            if r <=(m/(streamLength[0]+b_ind)):
                m_sample.pop(random.randrange(len(m_sample)))
                m_sample.append(batch)
            
    
    if batch_size > 0:
        print("Batch size at time [{0}] is: {1}".format(time, batch_size))
        
        
    streamLength[0] += batch_size
    if streamLength[0] >= n:
        stopping_condition.set()
        








if __name__ == '__main__':
    assert len(sys.argv) == 6, "USAGE: n, phi, epsilon, delta, port number"

    # IMPORTANT: when running locally, it is *fundamental* that the
    # `master` setting is "local[*]" or "local[n]" with n > 1, otherwise
    # there will be no processor running the streaming computation and your
    # code will crash with an out of memory (because the input keeps accumulating).
    conf = SparkConf().setMaster("local[*]").setAppName("DistinctExample")
    # If you get an OutOfMemory error in the heap consider to increase the
    # executor and drivers heap space with the following lines:
    # conf = conf.set("spark.executor.memory", "4g").set("spark.driver.memory", "4g")
    
    
    # Here, with the duration you can control how large to make your batches.
    # Beware that the data generator we are using is very fast, so the suggestion
    # is to use batches of less than a second, otherwise you might exhaust the memory.
    sc = SparkContext(conf=conf)
    ssc = StreamingContext(sc, 0.01)  # Batch duration of 0.01 seconds
    ssc.sparkContext.setLogLevel("ERROR")
    
    # TECHNICAL DETAIL:
    # The streaming spark context and our code and the tasks that are spawned all
    # work concurrently. To ensure a clean shut down we use this semaphore.
    # The main thread will first acquire the only permit available and then try
    # to acquire another one right after spinning up the streaming computation.
    # The second tentative at acquiring the semaphore will make the main thread
    # wait on the call. Then, in the `foreachRDD` call, when the stopping condition
    # is met we release the semaphore, basically giving "green light" to the main
    # thread to shut down the computation.
    # We cannot call `ssc.stop()` directly in `foreachRDD` because it might lead
    # to deadlocks.
    stopping_condition = threading.Event()
    
    
    # &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    # INPUT READING
    # &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

    
    
    n = int(sys.argv[1])
    
    phi = float(sys.argv[2])
    
    epsilon = float(sys.argv[3])
    
    delta = float(sys.argv[4])
    
    portExp = int(sys.argv[5])
    
    print("INPUT PROPERTIES")
    print("n =", n, "phi =", phi,"epsilon =", epsilon,"delta =", delta, "port = ", portExp)
        
    # &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    # DEFINING THE REQUIRED DATA STRUCTURES TO MAINTAIN THE STATE OF THE STREAM
    # &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

    streamLength = [0] # Stream length (an array to be passed by reference)
    histogram = {} # Hash Table for the distinct elements
    m_sample=[]

    # CODE TO PROCESS AN UNBOUNDED STREAM OF DATA IN BATCHES
    stream = ssc.socketTextStream("algo.dei.unipd.it", portExp, StorageLevel.MEMORY_AND_DISK)
    # For each batch, to the following.
    # BEWARE: the `foreachRDD` method has "at least once semantics", meaning
    # that the same data might be processed multiple times in case of failure.
    stream.foreachRDD(lambda time, batch: process_batch(time, batch))
    
    
    
    
    # MANAGING STREAMING SPARK CONTEXT
    print("Starting streaming engine")
    ssc.start()
    print("Waiting for shutdown condition")
    stopping_condition.wait()
    print("Stopping the streaming engine")
    # NOTE: You will see some data being processed even after the
    # shutdown command has been issued: This is because we are asking
    # to stop "gracefully", meaning that any outstanding work
    # will be done.
    ssc.stop(False, False)
    print("Streaming engine stopped")

    # COMPUTE AND PRINT FINAL STATISTICS
    counter=0
    freq_items=[]
    print(type(histogram))
    for key,value in histogram.items():
        if (value/streamLength[0])>= phi:
            counter+=1
            freq_items.append(key)
    
    print("EXACT ALGORITHM")
    print("Number of items in  the data structure =", len(histogram))
    print("Number of true frequent items =", len(freq_items))
    print("True frequent items:")
    for item in freq_items:
        print(item)
    
    
    # COMPUTE AND PRINT FINAL STATISTICS
    
    freq_items_r=[]
    t_f=[]
    
    for item in m_sample:
        if item not in freq_items_r:
            freq_items_r.append(item)
            
    for item in freq_items_r:
        if item not in freq_items:
            t_f.append("-")
        else :
            t_f.append("+")
    
    
    print("RESERVOIR SAMPLING")
    print("Size m of the sample =", np.ceil(1/phi))
    print("Number of estimated frequent items =", len(freq_items_r))
    print("Estimated frequent items:")
    for i in range(len(freq_items_r)):
        print(freq_items_r[i], t_f[i])
   
    
    