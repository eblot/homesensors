#!/bin/sh

back="${1:-2h}"

WIDTH=1000
HEIGHT=200

# Red
COLOR1="#FF5B00"
# Green
COLOR2="#98FB98"
# Gold
COLOR3="#FEC615"
# Blue
COLOR4="#247AFD"
# Purple
COLOR5="#BC13FE"

RRDTOOL=`which rrdtool`

${RRDTOOL} graph temp.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l-5 -u 25 --start -${back} --end now \
   -t Temperature --vertical-label="ºC" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t1=homesensor.rrd:temp_cave:AVERAGE \
   DEF:t2=homesensor.rrd:temp_jardin:AVERAGE \
   DEF:t3=homesensor.rrd:temp_garage:AVERAGE \
   DEF:t4=homesensor.rrd:temp_terrasse:AVERAGE \
   DEF:t5=homesensor.rrd:temp_roof:AVERAGE \
   LINE:t1${COLOR1}:"Cave\n" \
   LINE:t2${COLOR2}:"Jardin\n" \
   LINE:t3${COLOR3}:"Garage\n" \
   LINE:t4${COLOR4}:"Terrasse\n" \
   LINE:t5${COLOR5}:"Toit\n" \
&& $HOME/.iterm2/imgcat temp.png

${RRDTOOL} graph humi.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l 0 -u 100 --start -${back} --end now \
   -t Humidité --vertical-label="%" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t1=homesensor.rrd:humi_cave:AVERAGE \
   DEF:t2=homesensor.rrd:humi_jardin:AVERAGE \
   LINE:t1${COLOR1}:"Cave\n" \
   LINE:t2${COLOR2}:"Jardin\n" \
&& $HOME/.iterm2/imgcat humi.png

${RRDTOOL} graph rain.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l 0 -u 0.01 --start -${back} --end now \
   -t Pluie --vertical-label="mm" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t5=homesensor.rrd:rain_roof:AVERAGE \
   LINE:t5${COLOR5}:"Toit\n" \
&& $HOME/.iterm2/imgcat rain.png

#ADFF2F
