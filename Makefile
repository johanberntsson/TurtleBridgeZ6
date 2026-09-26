INFORM = inform
OZMOO = /home/johan/commodore/ozmoo
PUNY = /home/johan/commodore/punyinform

SFROTZ = sfrotz
XMEGA65 = xemu-xmega65 -besure

# make.rb anchors everything it reads to its own directory (asm/, tools/, temp/,
# exomizer) and writes the finished disk image into the CURRENT directory, so it
# can be called from here with plain relative paths -- no cd into $(OZMOO), no
# copying the image back. It also leaves the X16 build unpacked in
# x16_turtlebridge/ beside the zip, so there is nothing to unzip either.
OZMOOBUILD = ruby $(OZMOO)/make.rb

PICSRC   = resources/contents.yaml $(wildcard resources/*.png)
STORYSRC = turtlebridge.inf ../lib/ext_z6graphics.h $(wildcard $(PUNY)/lib/*.h)

all: sfrotz

turtlebridge.z6: $(STORYSRC) turtlebridge.blb
	$(INFORM) --opt OMIT_SYMBOL_TABLE=1 --define RUNTIME_ERRORS=0  +$(PUNY)/lib -v6 -es turtlebridge.inf

z6: turtlebridge.z6

turtlebridge.blb: $(PICSRC)
	python $(OZMOO)/tools/make_blorb.py resources

blorb: turtlebridge.blb

# Turtle Bridge has pictures but no sound effects, so there is no -asw here (Ozmoo
# stops with "No sound files found" if it is given a folder with no wavs).
x16_turtlebridge.zip: turtlebridge.blb turtlebridge.z6
	$(OZMOOBUILD) -t:x16 -pics turtlebridge.blb turtlebridge.z6

mega65_turtlebridge.d81: turtlebridge.blb turtlebridge.z6
	$(OZMOOBUILD) -t:mega65 -fcm -pics turtlebridge.blb turtlebridge.z6

mega65: mega65_turtlebridge.d81
	$(XMEGA65) -8 mega65_turtlebridge.d81

.PHONY: all z5-release z5-debug blorb z6 x16 mega65 test frotz sfrotz release clean

sfrotz: turtlebridge.z6 turtlebridge.blb
	# the blorb has to be named: sfrotz does not pick it up from the story name
	$(SFROTZ) turtlebridge.z6 turtlebridge.blb

clean:
	rm -rf turtlebridge.z5 turtlebridge.z6 turtlebridge.blb pics *.d64 *.d81 
