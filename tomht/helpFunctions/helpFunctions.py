import matplotlib.pyplot as plt
import numpy as np
import itertools
import pulp

def binomial(n,k):
    return 1 if k==0 else (0 if n==0 else binomial(n-1, k) + binomial(n-1, k-1))

def plotInitialTargets(initialTargets, **kwargs):
	for i, initialTarget in enumerate(initialTargets):
		index = kwargs.get("index",list(range(len(initialTargets))))
		if len(index) != len(initialTargets):
			raise ValueError("plotInitialTargets: Need equal number of targets and indecies")
		plt.plot(initialTarget.state[0],initialTarget.state[1],"k+")
		ax = plt.subplot(111)
		normVelocity = initialTarget.state[2:4] / np.linalg.norm(initialTarget.state[2:4])
		offset = 0.1 * normVelocity
		position = initialTarget.state[0:2] - offset
		ax.text(position[0], position[1], "T"+str(index[i]), 
			fontsize=8, horizontalalignment = "center", verticalalignment = "center")

def plotVelocityArrowFromNode(nodes, **kwargs):
	def recPlotVelocityArrowFromNode(node, stepsLeft):
		if node.predictedStateMean is not None:
			plotVelocityArrow(node)
		if stepsLeft > 0 and (node.parent is not None):
			recPlotVelocityArrowFromNode(node.parent, stepsLeft-1)
	for node in nodes:
		recPlotVelocityArrowFromNode(node, kwargs.get("stepsBack", 1))

def plotVelocityArrow(target):
	ax = plt.subplot(111)
	deltaPos = target.predictedStateMean[0:2] - target.filteredStateMean[0:2]
	ax.arrow(target.filteredStateMean[0], target.filteredStateMean[1], deltaPos[0], deltaPos[1],
	head_width=0.1, head_length=0.1, fc= "None", ec='k', 
	length_includes_head = "true", linestyle = "-", alpha = 0.3, linewidth = 1)

def plotRadarOutline(centerPosition, radarRange, **kwargs):
	from matplotlib.patches import Ellipse
	if kwargs.get("center", True):
		plt.plot(centerPosition.x, centerPosition.y,"bo")
	ax = plt.subplot(111)
	circle = Ellipse(centerPosition.toarray(), radarRange*2, radarRange*2)
	circle.set_facecolor("none")
	circle.set_linestyle("dotted")
	ax.add_artist(circle)

def plotCovarianceEllipse(cov, position, eta2):
	from matplotlib.patches import Ellipse
	lambda_, _ = np.linalg.eig(cov)
	ell = Ellipse( xy	 = (position.x, position.y), 
				   width = np.sqrt(lambda_[0])*np.sqrt(eta2)*2,
				   height= np.sqrt(lambda_[1])*np.sqrt(eta2)*2,
				   angle = np.rad2deg( np.arctan2( lambda_[1], lambda_[0]) ),
				   linewidth = 2,
				   )
	ell.set_facecolor('none')
	ell.set_linestyle("dotted")
	ell.set_alpha(0.5)
	ax = plt.subplot(111)
	ax.add_artist(ell)

def plotMeasurementList(measurmentList, scanNumber = None):
	for measurementIndex, measurement in enumerate(measurmentList.measurements):
		plotMeasurement(measurmentList, measurementIndex+1, scanNumber)

def plotMeasurementsFromList(scanHistory):
	for scanIndex, scan in enumerate(scanHistory):
		for measurementIndex, measurement in enumerate(scan.measurements):
			plotMeasurement(measurement, measurementIndex+1, scanIndex+1)

def plotMeasurementsFromForest(targetList, plotReal = True, plotDummy = True, **kwargs):
	from classDefinitions import Position
	def recPlotMeasurements(target, plottedMeasurements, plotReal, plotDummy):
		if target.parent is not None:
			if target.measurementNumber == 0:
				if plotDummy:
					plotMeasurement(target.getPosition(), target.measurementNumber, target.scanNumber)
			else:
				if plotReal:
					measurementID = (target.scanNumber,target.measurementNumber)
					if measurementID not in plottedMeasurements:
						plotMeasurement(target.measurement, target.measurementNumber, target.scanNumber)
						plottedMeasurements.add( measurementID )
		for hyp in target.trackHypotheses:
			recPlotMeasurements(hyp, plottedMeasurements, plotReal, plotDummy)
	
	plotReal = kwargs.get('real', plotReal)
	plotDummy = kwargs.get('dummy', plotDummy)
	if not (plotReal or plotDummy):
		return
	plottedMeasurements = set()
	for target in targetList:
		recPlotMeasurements(target,plottedMeasurements,plotReal, plotDummy)

def plotMeasurementsFromNodes(nodes, **kwargs):
	def recBactrackAndPlotMesurements(node, stepsBack = None, **kwargs):
		if node.parent is not None:
			if node.measurement is not None:
				plotMeasurement(node.measurement, node.measurementNumber, node.scanNumber, **kwargs)
			elif kwargs.get("dummy",False):
				plotMeasurement(node.getPosition(), node.measurementNumber, node.scanNumber, **kwargs)
			if stepsBack is None:
				recBactrackAndPlotMesurements(node.parent, None, **kwargs)
			elif stepsBack > 0:
				recBactrackAndPlotMesurements(node.parent, stepsBack-1, **kwargs)
	for node in nodes:
		recBactrackAndPlotMesurements(node, kwargs.get('stepsBack'), **kwargs)

def plotMeasurement(position, measurementNumber = None, scanNumber = None, **kwargs):
	x = position.x
	y = position.y
	if measurementNumber == 0:
		plt.plot(x,y,color = "black",fillstyle = "none", marker = "o")
	else:
		plt.plot(x, y,'kx')
	if (scanNumber is not None) and (measurementNumber is not None) and kwargs.get("labels",False):
		ax = plt.subplot(111)
		ax.text(x, y,str(scanNumber)+":"+str(measurementNumber), size = 7, ha = "left", va = "top") 

def plotValidationRegionFromNodes(nodes,eta2, stepsBack = 1):
	from classDefinitions import Position
	def recPlotValidationRegionFromNode(node, eta2, stepsBack):
		if node.residualCovariance is not None:
			plotCovarianceEllipse(node.residualCovariance, Position(node.predictedStateMean),eta2)
		if (node.parent is not None) and (stepsBack > 0):
			recPlotValidationRegionFromNode(node.parent, eta2, stepsBack-1)
	for node in nodes:
		recPlotValidationRegionFromNode(node, eta2, stepsBack)

def plotValidationRegionFromForest(targets, eta2, stepsBack = 1):
	def recPlotValidationRegionFromTarget(target, eta2, stepsBack):
		if not target.trackHypotheses:
			plotValidationRegionFromNodes([target], eta2, stepsBack)
		else:
			for hyp in target.trackHypotheses:
				recPlotValidationRegionFromTarget(hyp, eta2, stepsBack)

	for target in targets:
		recPlotValidationRegionFromTarget(target, eta2, stepsBack)

def plotActiveTrack(associationHistory):
	def recBacktrackPosition(target):
		if target.parent is None:
			return [target.getPosition()]
		return recBacktrackPosition(target.parent) + [target.getPosition()]
	colors = itertools.cycle(["r", "b", "g"])
	for hyp in associationHistory:
		positions = recBacktrackPosition(hyp)
		plt.plot([p.x for p in positions], [p.y for p in positions], c = next(colors))

def plotHypothesesTrack(targets):
	def recPlotHypothesesTrack(target, color = None, track = []):
		newTrack = track[:] + [target.getPosition()]
		if not target.trackHypotheses:
			if color is not None:
				plt.plot([p.x for p in newTrack], [p.y for p in newTrack], "--", c = color)
			else:
				plt.plot([p.x for p in newTrack], [p.y for p in newTrack], "--")
		else:
			for hyp in target.trackHypotheses:
				recPlotHypothesesTrack(hyp, color,  newTrack)
	colors = itertools.cycle(["r", "b", "g"])
	for target in targets:
		recPlotHypothesesTrack(target, next(colors))

def plotTrueTrack(simList, **kwargs):
	nScan = len(simList)
	nTargets = len(simList[0])
	posArray = np.zeros((nScan, nTargets, 2))
	for row, scan in enumerate(simList):
		posArray[row,:,:] = np.array([target.state[0:2] for target in scan])
	for col in range(nTargets):
		# plt.plot(posArray[:,col,0], posArray[:,col,1],'-.')
		# if kwargs.get("markers",False):
		plt.plot(posArray[:,col,0], posArray[:,col,1],'.', alpha = 0.2,markeredgewidth = 0.6)

def printScanList(scanList):
	for index, measurement in enumerate(scanList):
		print("\tMeasurement ", index, ":\t", end="", sep='')
		measurement.print()

def printClusterList(clusterList):
	print("Clusters:")
	for clusterIndex, cluster in enumerate(clusterList):
		print("Cluster ", clusterIndex, " contains target(s):\t", cluster, sep ="", end = "\n")
	
def printTargetList(targetList, **kwargs):
	print("TargetList:")
	for targetIndex, target in enumerate(targetList):
		if kwargs.get("backtrack", False):
			print(target.backtrack().__str__(targetIndex = targetIndex)) 
		else:
			print(target.__str__(targetIndex = targetIndex)) 
	print()

def printHypothesesScore(targetList):
	def recPrint(target, targetIndex):
		if not target.trackHypotheses:
			pass
		else:
			for hyp in target.trackHypotheses:
				recPrint(hyp, targetIndex)
	for targetIndex, target in enumerate(targetList):
		print(	"\tTarget: ",targetIndex,
 				"\tInit",	target.initial.position,
 				"\tPred",	target.predictedPosition(),
 				"\tMeas",	target.measurement,sep = "")

def nllr(*args):
	if len(args) == 1:
		P_d = args[0]
		if P_d == 1:
			return -np.log(1e-6)
		return -np.log(1-P_d)
	elif len(args) == 5:
		P_d 					= args[0]
		measurement 			= args[1]
		predictedMeasurement	= args[2]
		lambda_ex 				= args[3] 
		covariance 				= args[4]
		if (measurement is not None) and (predictedMeasurement is not None) and (lambda_ex is not None) and (covariance is not None):
			if lambda_ex == 0:
				print("RuntimeError('lambda_ex' can not be zero.)")
				lambda_ex += 1e-20
			measurementResidual = measurement.toarray() - predictedMeasurement
			return (	0.5*(measurementResidual.T.dot(np.linalg.inv(covariance)).dot(measurementResidual))
						+ np.log((lambda_ex*np.sqrt(np.linalg.det(2*np.pi*covariance)))/P_d) )
	else:
		raise TypeError("nllr() takes either 1 or 5 arguments (",len(args),") given")

def backtrackMeasurementsIndices(selectedNodes, steps = None):
	def recBacktrackNodeMeasurements(node, measurementBacktrack, stepsLeft = None):
		if node.parent is not None:
			if stepsLeft is None:
				measurementBacktrack.append(node.measurementNumber)
				recBacktrackNodeMeasurements(node.parent,measurementBacktrack)
			elif stepsLeft > 0:
				measurementBacktrack.append(node.measurementNumber)
				recBacktrackNodeMeasurements(node.parent,measurementBacktrack, stepsLeft-1)
	measurementsBacktracks = []
	for node in selectedNodes:
		measurementBacktrack = []
		recBacktrackNodeMeasurements(node, measurementBacktrack, steps)
		measurementBacktrack.reverse()
		measurementsBacktracks.append(measurementBacktrack)
	return measurementsBacktracks

def backtrackNodePositions(selectedNodes, **kwargs):
	from classDefinitions import Position
	def recBacktrackNodePosition(node, measurementList):
		measurementList.append(Position(node.filteredStateMean[0:2]))
		if node.parent is not None:
			if node.parent.scanNumber != node.scanNumber-1:
				print()
				print(node.backtrack(3))
				raise ValueError("Inconsistent scanNumber-ing:", node.scanNumber,"->", node.parent.scanNumber)
			recBacktrackNodePosition(node.parent, measurementList)

	try:
		trackList = []
		for leafNode in selectedNodes:
			measurementList = []
			recBacktrackNodePosition(leafNode,measurementList)
			measurementList.reverse()
			trackList.append(measurementList)
		return trackList
	except ValueError as e:
		if kwargs.get("debug",False):
			print(e)
		raise

def writeTracksToFile(filename,trackList, time, **kwargs):
	f = open(filename,'w')
	for targetTrack in trackList:
		s = ""
		for index, position in enumerate(targetTrack):
			s += str(position)
			s += ',' if index != len(targetTrack)-1 else ''
		s += "\n"
		f.write(s)
	f.close()

def parseSolver(solverString):
	s = solverString.strip().lower()
	if s == "cplex":
		return pulp.CPLEX_CMD(None, 0,1,0,[],0.05)
	if s == "glpk":
		return pulp.GLPK_CMD(None, 0,1,0,[])
	if s == "cbc":
		return pulp.PULP_CBC_CMD()
	if s == "gurobi":
		return pulp.GUROBI_CMD(None, 0,1,0,[])
	return None

def solverIsAvailable(solverString):
	s = solverString.strip().lower()
	if s == "cplex":
		return pulp.CPLEX_CMD().available() != False
	if s == "glpk":
		return pulp.GLPK_CMD().available() != False
	if s == "cbc":
		return pulp.PULP_CBC_CMD().available() != False
	if s == "gurobi":
		return pulp.GUROBI_CMD().available() != False
	return False

# import cProfile
# import pstats
# p = cProfile.runctx('_solveBLP(A1,A2, C)',None,locals(), filename = 'restats')
# p = pstats.Stats('restats')
# p.sort_stats('cumulative').print_stats(20)
