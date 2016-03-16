#python
import lx
'''
This script uses a faceshift target file to relink the BVH blendshape joints to the respective morph strength channels
Select the mesh you want and then call the script.
'''

fsMorphs = [] # faceShift morphs in the target file
assetMorphs = [] # expected morphs mapped to the faceShift morphs in the targetfile.
fslocator_IDList = [] # locator IDs parented to our Blendshapes locator.
fslocator_NameList = [] # locator names for our IDs.
morphInfluenceIDs = [] # morph deformer IDs belonging to our mesh item(s) in the scene.

def parseTarget(targetFile):
	global fsMorphs
	global assetMorphs
	with open(targetFile) as f:
		content = f.read().splitlines()
	# Let's find the beginning of our relationship definition section.
	line = 0
	while (not content[line].startswith('bs')):
		if (line == len(content)):
			# Didn't find anything, we'll exit
			lx.out('Could not find data in file!')
			sys.exit()
		line += 1
	# OK, we found something.
	# Each line now should be of the form : bs = EyeSquint_R = Victoria4_unwelded_blendShape.head.PHMEyeSquintR = 2
	monitor = lx.Monitor( len(content) )
	monitor.step()
	while (line < len(content)):
		tempArray = content[line].split(' = ')
		faceShiftMorph = tempArray[1]
		myAssetMorph = tempArray[2]
		# take our *_blendShape. off the front.
		myAssetMorph = myAssetMorph[(myAssetMorph.index('.') + 1):]
		# OK. We can't use dictionaries here because each morph can appear more than once. So we use a pair of matched arrays
		fsMorphs.append(faceShiftMorph)
		assetMorphs.append(myAssetMorph)
		line += 1
		monitor.step()

	for item in range(len(fsMorphs)):
		lx.out("fsmorph {%s} matched to assetmorph {%s}" % (fsMorphs[item], assetMorphs[item]))

def linkMorphs(meshID):
	global assetMorphs
	global fsMorphs
	global morphInfluenceIDs
	global fslocator_IDList
	global fslocator_NameList

	# We need a list of locators that match our expectations for the faceShift imported dataset.
	# This populates our fslocator_IDList and fslocator_NameList lists
	prepareLocatorList()

	# Now we need the morph influences against our selected mesh item
	# This populates our morphInfluenceIDs list
	findMorphInfluences(meshID)

	# OK so we need by morph deformers and check that the associated  morph map property matches our faceShift-associated morph.
	monitor = lx.Monitor( len(morphInfluenceIDs) )     
	lx.out('Processing morph influences')
	for index in range(len(morphInfluenceIDs)):
		lx.out("Number of influences in total {%s}" % len(morphInfluenceIDs))
		morphID = morphInfluenceIDs[index]

		# We need to extract our map name from this deformer.
		lx.eval('select.deformer {%s} set' % morphID)
		morphMapName = lx.eval('item.channel mapName ? {%s}' % morphID)

		# So we have a valid deformer and the associated map.
		# Let's see if the morph map was used in faceShift
		# morphIndices will hold the position(s) of the map in the assetMorphs array.
		morphIndices = indices(assetMorphs, morphMapName)

		if (len(morphIndices) > 0):
			lx.out('morphs to process : {%d}' % len(morphIndices))
			for index in range(len(morphIndices)):
				# Retrieve the corresponding faceshift morph name
				fsMorphName = fsMorphs[morphIndices[index]]

				# Retrieve the locator ID from the matched array based on the name
				fsLink_Locator_ID = fslocator_IDList[fslocator_NameList.index(fsMorphName)]
				# We need the xfrmScl locator for this locator.
				scl_xfrm_item = lx.eval('query sceneservice item.xfrmScl ? {%s}' % fsLink_Locator_ID)

				# Select our driver channel first
				lx.out('Selecting locator {%s} channel scl.Z' % scl_xfrm_item)
				lx.eval('select.channel {%s:%s} set' % (scl_xfrm_item, "scl.Z"))

				# Select our morph influence strength channel next.
				lx.out('Selecting morph {%s} channel strength' % morphID)
				lx.eval('select.channel {%s:%s} add' % (morphID, "strength"))

				# Link them together
				lx.eval('channel.link toggle')
		monitor.step()

def indices(lst, element):
	result = []
	offset = -1
	while True:
		try:
			offset = lst.index(element, offset+1)
		except ValueError:
			return result
		result.append(offset)

def prepareLocatorList():
	global fslocator_IDList
	global fslocator_NameList
	locatorNames = []
	locatorIDs = []
	lx.out('Prepping locator list')
	numberOfSceneItems = lx.eval('query sceneservice item.N ?')
	monitor = lx.Monitor( numberOfSceneItems )     
	for i in range(numberOfSceneItems):
		type = lx.eval('query sceneservice item.type ? %s' % i)
		if (type == "locator"):
			locatorIDs.append(lx.eval('query sceneservice item.id ? %s' % i))
			locatorNames.append(lx.eval('query sceneservice item.name ? %s' % i))
		monitor.step()
	monitor = lx.Monitor( len(locatorIDs) )     
	for index in range(len(locatorIDs)):
		myParentID = lx.eval('query sceneservice item.parent ? {%s}' % locatorIDs[index])
		if (myParentID != None):
			myParentName = lx.eval('query sceneservice item.name ? {%s}' % myParentID)
			if (myParentName == "Blendshapes"):
				fslocator_IDList.append(lx.eval('query sceneservice item.id ? {%s}' % locatorIDs[index]))
				fslocator_NameList.append(lx.eval('query sceneservice item.name ? {%s}' % locatorNames[index]))
		monitor.step()

def findMorphInfluences(meshID):
	global morphInfluenceIDs
	lx.out('Finding morph influences')
	numberOfDeformers = lx.eval('query sceneservice morphDeform.N ?')
	lx.out('Morph influences : {%d}' % numberOfDeformers)
	monitor = lx.Monitor( numberOfDeformers )     
	for influence in range(numberOfDeformers):
		currentMorphID = lx.eval('query sceneservice morphDeform.id ? {%s}' % influence)
		currentMorphName = lx.eval('query sceneservice morphDeform.name ? {%s}' % influence)
		deformerMeshID = lx.eval('query sceneservice deformer.meshes ? {%s}' % currentMorphID)
		lx.out('Deformer mesh name is : {%s}' % deformerMeshID)
		if (meshID == deformerMeshID):
			lx.out('Matched influence {%s} to mesh {%s}' %(currentMorphName, deformerMeshID))
			morphInfluenceIDs.append(currentMorphID)
		monitor.step()

def main():
	meshIDs = lx.evalN('query sceneservice selection ? mesh')
	if (len(meshIDs) == 0):
		lx.out('At least one mesh must be selected to create links')
		sys.exit()
	targetFile = customfile('fileOpen', 'Load Target file', 'fst', 'FST', '*.fst', None)
	if (targetFile != None):
		parseTarget(targetFile)
	else:
		sys.exit()
	for meshID in meshIDs:
		linkMorphs(meshID)

# From Gwynne Reddick
def customfile(type, title, format, uname, ext, save_ext=None, path=None):
	'''
		Open a file requester for a custom file type and return result
		type - open or save dialog (fileOpen or fileSave)
		title - dialog title
		format - file format
		uname - format username
		ext - file extension in the form '*.ext'
		save_ext - (optional)
		path - (optional) Default path to open dialog with
		
		examples:
			file = customfile('fileOpen', 'Open JPEG file', 'JPG', 'JPEG File', '*.jpg;*.jpeg')
			file = customfile('fileSave', 'Save Text file', 'TXT', 'Text File', '*.txt', 'txt')
	
	'''
	lx.eval('dialog.setup %s' % type)
	lx.eval('dialog.title {%s}' % (title))
	lx.eval('dialog.fileTypeCustom {%s} {%s} {%s} {%s}' % (format, uname, ext, save_ext))
	if type == 'fileSave' and save_ext != None:
		lx.eval('dialog.fileSaveFormat %s' % save_ext)
	if path != None:
		lx.eval('dialog.result {%s}' % (path + 'Scenes'))
	try:
		lx.eval('dialog.open')
		return lx.eval('dialog.result ?')
	except:
		return None

	#stlfile = customfile('fileOpen', 'Load STL file', 'stl', 'STL', '*.stl')

main()