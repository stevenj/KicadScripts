#  Copyright 2015 Steven Johnson <strntydog@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""
Execute this to load this scripts into the console the first time.
import UserScripts.ViaStitching

After editing this scripts, execute this in the console to reload and run.

reload(UserScripts.ViaStitching)
UserScripts.ViaStitching.StitchVias()
"""
import pcbnew
import math, sys, time

if 'EXTERNAL_DEBUG' not in globals():
  global EXTERNAL_DEBUG
  EXTERNAL_DEBUG=False

if 'DEBUG' not in globals():
  global DEBUG
  DEBUG=False

if EXTERNAL_DEBUG:
  import rpdb2;

ToUnits=pcbnew.ToMM
FromUnits=pcbnew.FromMM

def Prompt(msg = "Press ENTER to Continue : ",
           compare = "",
           canstop = True):
  """
  Print a prompt, wait for a response, return True if the response is
  the same as the "compare" parameter (case insensitive).

  msg - The prompt.  Defaults to "Press ENTER to Continue : "
  compare - The True response. Defaults to ""
  canstop - If the input can stop the script.  Defaults to True.

  If canstop is True, "(Type STOP to Quit) " is added to the prompt.
  If "STOP" is entered, the script terminates.
  """

  if canstop:
    msg = msg + "(Type 'STOP' to Quit) "

  response = raw_input(msg)

  response = response.strip().lower()

  if "stop" == response:
    print "Ignore this exception, its just how it works...."
    exit(1)

  return (compare.strip().lower() == response)

def line_step(start, end, step):
  """
  Caculates the X and Y step to take to move "step" distance along the line.

  start - The start point of the line
  end   - The end point of the line
  step  - the distance to step along the line.

  Returns a tupple:
    ( xstep, ystep, number of steps)
    xstep : the distance to step in X
    ystep : the distance to step in Y
    steps : the number of steps you can take before you run over the end of the line.
  """
  a = end[0] - start[0]
  b = end[1] - start[1]
  c = math.sqrt((a*a)+(b*b))

  stepscale = c / step
  xstep = a / stepscale
  ystep = b / stepscale

  if DEBUG:
    print "line_step: a=%d, b=%d, c=%d, stepscale=%d, xstep=%d, ystep=%d" % (a,b,c,stepscale,xstep,ystep)

  # xstep is the distance to step in the x-direction.
  # ystep is the distance to step in the y-direction.
  # stepscale is the total number of steps to take.
  return (xstep, ystep, stepscale)

def line(start, end, step):
  """
  Stepped line coordinate genertor.

  Iterates from start to end, and yields co-ordiantes that are "step" distance apart.

  start : start point of the line.
  end   : end point of the line.
  step  : distance to step.

  The first coordinate yielded is always "start"
  The last  coordinate yielded is the the last whole step before or on "end".
  """
  steps = line_step(start,end,step)

  step = 0
  while step <= steps[2]:
    x = start[0] + (step * steps[0])
    y = start[1] + (step * steps[1])
    yield [x, y]
    step = step+1

def IsLocked(item):
  """
  Check if the particular "item" is locked.

  item - the item to check.

  returns True if the item is locked, False otherwise.
  """
  return (item.GetState(pcbnew.TRACK_LOCKED) != 0)

def ConnectUnconnectedVias(board=None, net="GND", dryrun=True):
  """ Connect ALL Unconnected vias to the specified NET.
      Use it to fix up after a DRC check, or if the Stitching Vias loose their Net.

  board  -- the board to process, defaults to the one in the editor.
  net    -- the net to rip up.  Defaults to "GND"
  dryrun -- Defaults to True, wont actually rip up anything unless its False.
  """
  if board == None:
      print "Loading the Board on screen"
      board = pcbnew.GetBoard()

  vianet = board.FindNet(net)
  if vianet == None:
    return None

  print "SETTING UNCONNECTED VIAS TO NET -- %s:" % (net)
  for item in board.GetTracks():
    if (type(item) is pcbnew.VIA):
      code = item.GetNetCode()
      name = item.GetNetname()
      print "  VIA   : Net %s is Code %d" % (name, code)


def RipupUnlocked(board=None, net="GND", dryrun=True):
  """ Ripup all vias and tracks of a particular net, as long as they are NOT locked.

  board  -- the board to process, defaults to the one in the editor.
  net    -- the net to rip up.  Defaults to "GND"
  dryrun -- Defaults to True, wont actually rip up anything unless its False.
  """

  if board == None:
      print "Loading the Board on screen"
      board = pcbnew.GetBoard()

  print "RIPPING UP UNLOCKED VIAS/TRACKS ON NET -- %s:" % (net)
  for item in board.GetTracks():
    if (type(item) is pcbnew.VIA):
      if (net == item.GetNetname()):
        pos = item.GetPosition()

        if IsLocked(item) :
          print "  VIA   : Skipping LOCKED %s VIA @ %s" % (net, ToUnits(pos))
        else:
          print "  VIA   : Ripping UP %s VIA @ %s" % (net, ToUnits(pos))
          if not dryrun:
            item.DeleteStructure()
          else:
            print "          Ripup not performed - DRYRUN."
    elif (type(item) is pcbnew.TRACK):
      if (item.GetNetname() == net):
        start = item.GetStart()
        end = item.GetEnd()

        if IsLocked(item):
          print "  TRACK : Skipping LOCKED %s TRACK : %s to %s" % (net, ToUnits(start), ToUnits(end))
        else:
          print "  TRACK : Ripping UP %s TRACK @ %s to %s" % (net, ToUnits(start), ToUnits(end))
          if not dryrun:
            item.DeleteStructure()
          else:
            print "          Ripup not performed - DRYRUN."
    else:
      print "  ????? : Unknown type %s" % type(item)

def MakeVia(board, vtype = pcbnew.VIA_THROUGH, net = None, top = True):
  """
  Make a via.

  board -- The board you want to make the VIA for.
           NO DEFAULT, you have to supply this parameter.
  vtype -- is the type of via to make. Either :
           pcbnew.VIA_THROUGH (default) or
           pcbnew.VIA_MICROVIA
  net   -- The net name to associate the Via with.
  top   -- Only for microvias.
           True means a Microvia on the top layer.
           False means a Microvia on the bottom layer.
  """
  vianet = board.FindNet(net)
  if vianet == None:
    return None

  v = pcbnew.VIA(board)
  v.SetNetCode(vianet.GetNet())
  v.SetViaType(vtype)

  if (vtype == pcbnew.VIA_THROUGH) :
    v.SetWidth(vianet.GetViaSize())
    v.SetDrill(vianet.GetViaDrillSize())
    v.SetLayerPair( pcbnew.B_Cu, pcbnew.F_Cu )
  elif (vtype == pcbnew.VIA_MICROVIA) :
    v.SetWidth(vianet.GetMicroViaSize())
    v.SetDrill(vianet.GetMicroViaDrillSize())
    if top == True :
      v.SetLayerPair( pcbnew.F_Cu, pcbnew.In1_Cu )
    else :
      v.SetLayerPair( pcbnew.B_Cu, pcbnew.In30_Cu )
  else:
    return None

  return v

def StitchVias(stitch=0, fill=0, layer="Eco2.User", net="GND", microvia=True):
  """ Fill a board with Stitching Vias.

    Keyword arguments:
    stitch   -- The spacing to put the stitching on, in mm.
                0 = Use net Default Via Size * 2.
                -1 = Dont Stitch.
                (Default : 0)
    fill     -- The spacing to put the fill on, in mm.
                0 = Use net Default Via Size * 4.
                -1 = Dont Fill.
                (Default : 0)
    layer    -- the layer to find the stitching guides on.
                (Default : "Eco2.User")
    net      -- the net to assign to the VIA.
                (Default : "GND")
    microvia -- If to use microvias, in addition to normal vias.
                (Default : True)

    How it works:

    0. Rip up Non-Locked Vias and Tracks off the Net. (Cleanup pass)
    1. Read the lines on the guide layer.
    2. Step along the lines, placing a via every "spacing" gap apart.
    3. Create a outline box of the outside edge of the guide lines.
    4. Step along inside the outline box at "fill" distance apart and
       place a via.

    Placing a Via,
      For a 2 layer board, it just places a via.
      For a 4 layer board, first try and place a through hole via.
        IF the via can not be placed, try a microvia between Top and inner layer.
        Then a microvia between the Bottom and inner layer.
      For a 6+ layer board, I didnt implement that, feel free to add it.

      During Stitching, placing a via wont occur if it would colide with
      another via.

      During FILL, placing a via wont occur if another via is within the current spacing
      of the fill.
  """

  #if EXTERNAL_DEBUG:
    #print "Connect winpdb NOW... Password is 'password'"
    #time.sleep(30)
    #rpdb2.start_embedded_debugger("password")

  print "Hopefully I can make this put vias all over the GND plane..."
  print "Just hoping though..."

  print "Loading the Board on screen"
  board = pcbnew.GetBoard()

  print "Getting information about NET %s" % net
  vianet = board.FindNet(net)
  if vianet == None:
    print "ERROR : NET %s can not be found on this board. Aborting."
    return False

  # Fix up Stitch parameter
  if stitch != -1:
    if stitch == 0:
      stitch = vianet.GetViaSize() * 2
    else:
      stitch = ToUnits(stitch)

  # Fix up Fill parameter
  if fill != -1:
    if fill == 0:
      fill = vianet.GetViaSize() * 4
    else:
      fill = ToUnits(fill)

  guides = []

  print "Cleaning the unlocked net VIAS and TRACKS Before stitching."
  print "WARNING : Proceeding will cause all unlocked Tracks and Vias of the net to be deleted!!"
  Prompt()

  RipupUnlocked(board, net, dryrun=False)

  Prompt()

  print "Getting all of the VIA Guides from the specified layer:"
  for item in board.GetDrawings():
    if type(item) is pcbnew.DRAWSEGMENT:
      if layer == item.GetLayerName():
        start = item.GetStart()
        end   = item.GetEnd()

        if DEBUG:
          print "* Drawing: %s - %s, %s: %s, %s" % (item.GetShapeStr(),
                     item.GetLayer(),
                     item.GetLayerName(),
                     start,end)

        guides = guides + [[start, end]]

        if DEBUG:
          print "%s, %s" % (dir(item), vars(item))

  if DEBUG:
    print guides

  if stitch == -1:
    print "Stitching Disabled, NOT STITCHING"
  else :
    print "Tracing along the guides and placing vias at the required stitch distance."

    for guide in guides:
      print "Guide at : %s to %s" % (guide[0], guide[1])
      for via_point in line(guide[0], guide[1], stitch):
        print "  Via at: %s" % (via_point)
        v = MakeVia(board, vtype = pcbnew.VIA_THROUGH, net = net)
        v.SetPosition(pcbnew.wxPoint(via_point[0], via_point[1]))
        pcbnew

  if fill == -1:
    print "Filling Disabled, NOT FILLING"
  else :
    print "Rasterising the bounding box of the Guides, and filling... Somehow"
