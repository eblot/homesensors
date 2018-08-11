#!/bin/sh

back="${1:-2h}"
rrdfile="${2:-sensor.rrd}"

WIDTH=1000
HEIGHT=200

# https://en.wikipedia.org/wiki/Web_colors

# Red
COLOR1="#FF5B00"
# Forest Green
COLOR2="#228B22"
# Grey
COLOR3="#BBBBBB"
# Blue
COLOR4="#247AFD"
# Purple
COLOR5="#BC13FE"
# Pale Green
COLOR6="#98FB98"
# Light yellow
COLOR7="#FFE4B5"
# Sienna
COLOR8="#A0522D"

RRDTOOL=`which rrdtool`

${RRDTOOL} graph temp.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l-5 -u 25 --start -${back} --end now \
   -t Temperature --vertical-label="ºC" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t1=${rrdfile}:temp_cave:AVERAGE \
   DEF:t2=${rrdfile}:temp_jardin:AVERAGE \
   DEF:t3=${rrdfile}:temp_garage:AVERAGE \
   DEF:t4=${rrdfile}:temp_terrasse:AVERAGE \
   DEF:t5=${rrdfile}:temp_toit:AVERAGE \
   DEF:t6=${rrdfile}:temp_extension:AVERAGE \
   DEF:t7=${rrdfile}:temp_salle:AVERAGE \
   DEF:t8=${rrdfile}:temp_chambre:AVERAGE \
   LINE:t1${COLOR1}:"Cave\n" \
   LINE:t2${COLOR2}:"Jardin\n" \
   LINE:t3${COLOR3}:"Garage\n" \
   LINE:t4${COLOR4}:"Terrasse\n" \
   LINE:t5${COLOR5}:"Toit\n" \
   LINE:t6${COLOR6}:"Extension\n" \
   LINE:t7${COLOR7}:"Salle\n" \
   LINE:t8${COLOR8}:"Chambre\n" \
&& $HOME/.iterm2/imgcat temp.png

${RRDTOOL} graph humi.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l 0 -u 100 --start -${back} --end now \
   -t Humidité --vertical-label="%" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t1=${rrdfile}:humi_cave:AVERAGE \
   DEF:t2=${rrdfile}:humi_jardin:AVERAGE \
   DEF:t6=${rrdfile}:humi_extension:AVERAGE \
   DEF:t7=${rrdfile}:humi_salle:AVERAGE \
   DEF:t8=${rrdfile}:humi_chambre:AVERAGE \
   LINE:t1${COLOR1}:"Cave\n" \
   LINE:t2${COLOR2}:"Jardin\n" \
   LINE:t6${COLOR6}:"Extension\n" \
   LINE:t7${COLOR7}:"Salle\n" \
   LINE:t8${COLOR8}:"Chambre\n" \
&& $HOME/.iterm2/imgcat humi.png

${RRDTOOL} graph rain.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l 0 -u 0.01 --start -${back} --end now \
   -t Pluie --vertical-label="mm" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t5=${rrdfile}:rain_toit:AVERAGE \
   LINE:t5${COLOR5}:"Toit\n" \
&& $HOME/.iterm2/imgcat rain.png

${RRDTOOL} graph battery.png \
   -w ${WIDTH} -h ${HEIGHT} -a PNG --slope-mode \
   -l 0 -u 0.01 --start -${back} --end now \
   -t Pluie --vertical-label="mm" \
   -c BACK#2f2f2f -c CANVAS#0f0f0f -c FONT#efefef \
   --legend-position=east \
   DEF:t1=${rrdfile}:batt_cave:AVERAGE \
   DEF:t2=${rrdfile}:batt_jardin:AVERAGE \
   DEF:t6=${rrdfile}:batt_extension:AVERAGE \
   DEF:t7=${rrdfile}:batt_salle:AVERAGE \
   DEF:t8=${rrdfile}:batt_chambre:AVERAGE \
   LINE:t1${COLOR1}:"Cave\n" \
   LINE:t2${COLOR2}:"Jardin\n" \
   LINE:t6${COLOR6}:"Extension\n" \
   LINE:t7${COLOR7}:"Salle\n" \
   LINE:t8${COLOR8}:"Chambre\n" \
&& $HOME/.iterm2/imgcat battery.png

#ADFF2F
