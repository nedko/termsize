termsize: termsize.c
	cc -o termsize termsize.c

README.html:
	asciidoc -b html5 -a data-uri -a icons --theme ladi -o README.html README.adoc
