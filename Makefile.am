ACLOCAL_AMFLAGS = -I m4 -I libgd
NULL =

bin_SCRIPTS = gnome-music

SUBDIRS = libgd gnomemusic data po

EXTRA_DIST = \
	AUTHORS.in \
	gnome-music.in
	$(NULL)

CLEANFILES = \
	$(bin_SCRIPTS)
	$(NULL)

MAINTAINERCLEANFILES = \
	$(srcdir)/AUTHORS \
	$(srcdir)/INSTALL \
	$(srcdir)/aclocal.m4 \
	$(srcdir)/autoscan.log \
	$(srcdir)/compile \
	$(srcdir)/config.guess \
	$(srcdir)/config.h.in \
	$(srcdir)/config.sub \
	$(srcdir)/configure.scan \
	$(srcdir)/depcomp \
	$(srcdir)/install-sh \
	$(srcdir)/ltmain.sh \
	$(srcdir)/missing \
	$(srcdir)/mkinstalldirs \
	$(NULL)

GITIGNOREFILES = \
	m4 \
	$(NULL)

dist-hook: gen-AUTHORS

gen-AUTHORS:
	$(AM_V_GEN)if test -d $(srcdir)/.git; then                      \
	   out="`cd $(srcdir) && git log --pretty=format:'%aN <%aE>' | sort -u`" && \
	   perl -p -e "s/#authorslist#// and print '$$out'"            \
	     < $(srcdir)/AUTHORS.in > $(distdir)/AUTHORS-tmp &&        \
	   mv -f $(distdir)/AUTHORS-tmp $(distdir)/AUTHORS ;           \
	fi

gnome-music: gnome-music.in
	sed						\
		-e s!\@srcdir\@!$(abs_top_srcdir)!	\
		-e s!\@prefix\@!$(prefix)!		\
		-e s!\@datadir\@!$(datadir)!		\
		-e s!\@pkgdatadir\@!$(pkgdatadir)!	\
		-e s!\@libexecdir\@!$(libexecdir)!	\
		-e s!\@libdir\@!$(libdir)!		\
		-e s!\@pkglibdir\@!$(pkglibdir)!	\
		-e s!\@localedir\@!$(localedir)!	\
		-e s!\@pythondir\@!$(pythondir)!	\
		-e s!\@pyexecdir\@!$(pyexecdir)!	\
		-e s!\@PACKAGE\@!$(PACKAGE)!		\
		-e s!\@VERSION\@!$(VERSION)!		\
		< $< > $@
	chmod a+x $@

gnome-music: Makefile

all-local: gnome-music

-include $(top_srcdir)/git.mk

