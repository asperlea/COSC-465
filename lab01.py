##############################################

def mb_checksum(s):
	numlist = []
	for ch in s: #create list of nums
		numlist.append(ord(ch))

	checksum = 0
	for i in range(8): #count how many bits are in each position
		num_ones = 0
		for num in numlist:
			if num & (1 << i):
				num_ones += 1
		if num_ones % 2 == 1: #if there was an odd number of ones add a one at that position in the checksum
			checksum |= (1 << i)
	return chr(checksum)

##############################################

tests = {
    'A': 0x41,
    'OK': 0x04,
    'Test': 0x36,
    'Hello, world': 0x2c,
    "OK @system::2014/01/16 11:44:59:: Don't kiss an elephant on the lips today.::@system::2014/01/16 11:45:02:: You will be run over by a truck.": 0x1a,
}

for s,csum in tests.iteritems():
    print "Checking {0}".format(s)
    computed = mb_checksum(s)
    if chr(csum) == computed:
        print "Checksum for {0} looks ok".format(s)
    else:
        print "Checksum for {0} isn't correct: you got {1} but it should have been {2}".format(s, hex(ord(computed)), hex(csum))
    

