filename datain url 'http://data.sfgov.org/resource/vw6y-z8j6.csv?$limit=5000&$$app_token=YOURAPPTOKENHERE';
proc import datafile=datain out=dataout dbms=csv replace;
  getnames=yes;
run;