%global _hardened_build 1

%global commit 7257dbc58fe27ec3b1b573707bb0a8f6fde3d462
%global shortcommit %(c=%{commit}; echo ${c:0:7})

%global services hbase-master.service hbase-thrift.service hbase-rest.service hbase-zookeeper.service hbase-regionserver.service hbase-master-backup.service

# Currently disabled because packaging the singular binary in a noarch package
# is troublesome
%global package_native 0

# Disable running the test suite by default
%bcond_with tests

# Disable javadoc generation by default
%bcond_with javadoc

Name: hbase
Version: 0.98.3
Release: 1%{?dist}
Summary: A database for Apache Hadoop
License: ASL 2.0
URL: http://hbase.apache.org/
Source0: https://github.com/apache/hbase/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
Source1: %{name}.logrotate
Source2: %{name}-site.xml
Source3: %{name}.service.template
Patch0: %{name}-fedora-integration.patch
# Changes for java8
Patch1: %{name}-java8.patch
# Update to guava 17.0
Patch2: %{name}-guava.patch
BuildArch: noarch
# There is no hadoop on ARM
ExcludeArch: %{arm}

BuildRequires: bytelist
BuildRequires: cmake
BuildRequires: gcc-c++
BuildRequires: eclipse-m2e-core
BuildRequires: findbugs
BuildRequires: hadoop-client
BuildRequires: hadoop-tests
BuildRequires: high-scale-lib
BuildRequires: htrace
BuildRequires: jamon-maven-plugin
BuildRequires: jansi
BuildRequires: jcodings
BuildRequires: jetty-jsp
BuildRequires: jline
BuildRequires: jnr-constants
BuildRequires: jnr-posix
BuildRequires: joda-time
BuildRequires: joni
BuildRequires: jruby
BuildRequires: make
BuildRequires: maven-antrun-plugin
BuildRequires: maven-clean-plugin
BuildRequires: maven-dependency-plugin
BuildRequires: maven-eclipse-plugin
BuildRequires: maven-failsafe-plugin
BuildRequires: maven-install-plugin
BuildRequires: maven-local
BuildRequires: metrics
BuildRequires: objectweb-asm
BuildRequires: objectweb-asm3
BuildRequires: snappy-java
BuildRequires: systemd
BuildRequires: xml-maven-plugin

# Required for the shell
Requires: bytelist
Requires: invokebinder
Requires: jcodings
Requires: jansi
Requires: jline
Requires: jnr-ffi
Requires: jnr-posix
Requires: jnr-constants
# Documenting the dep here, but it's detected in autoRequires
# Requires: jruby
Requires: joda-time
Requires: joni
Requires: objectweb-asm

Requires: apache-commons-lang3
Requires: glassfish-el-api

Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

%description
Apache HBase is a database for Apache Hadoop that provides a distributed,
scalable, big data store.

%if %{package_native}
%package native
Summary: Native Apache HBase libraries
Requires: %{name} = %{version}-%{release}

%description native
Apache HBase is a database for Apache Hadoop that provides a distributed,
scalable, big data store.

This package contains native libraries for Apache HBase.
%endif

%if %{with javadoc}
%package javadoc
Summary: Javadoc for Apache HBase
BuildArch: noarch

%description javadoc
This package contains the API documentation for %{name}.
%endif

%package tests
Summary: Apache HBase test resources
BuildArch: noarch
Requires: %{name} = %{version}-%{release}
Requires: hadoop-tests

%description tests
Apache HBase is a database for Apache Hadoop that provides a distributed,
scalable, big data store.

This package contains test related resources for Apache HBase.

%prep
%setup -qn %{name}-%{commit}
%patch0 -p1
%patch1 -p1
%patch2 -p1

# Remove the findbugs-maven-plugin.  It's not needed and isn't available
%pom_remove_plugin :findbugs-maven-plugin
%pom_remove_plugin :findbugs-maven-plugin hbase-shell
%pom_remove_plugin :findbugs-maven-plugin hbase-server

# Remove apache-rat-plugin because it causes build failure on xmvn generated
# files
%pom_remove_plugin org.apache.rat:apache-rat-plugin

# Change findbugs-annotation gid:aid
sed -i "s/com.github.stephenc.findbugs/com.google.code.findbugs/" pom.xml
sed -i "s/Id>findbugs-annotations/Id>annotations/" pom.xml

# Fix surefire plugin config: perThread -> perthread
sed -i "s/perThread/perthread/" pom.xml

# Create separate file lists for packaging
%mvn_package :%{name}-testing-util::{}: %{name}-tests
%mvn_package :::tests: %{name}-tests

# Add test scope for hbase-common-tests to hbase-prefix-tree
%pom_xpath_inject "pom:project/pom:dependencies/pom:dependency[pom:artifactId='hbase-common' and pom:classifier='tests']" "
      <scope>test</scope>
" hbase-prefix-tree

%build
%if %{package_native}
profile="-Pnative"
%endif
%if %{without javadoc}
opts="-j"
%endif
%mvn_build $opts -- $profile clean install -DskipTests assembly:single -Prelease

%if %{with tests}
%check
%if %{package_native}
profile="-Pnative"
%endif
xmvn -o -Dhadoop.profile=2.0 $profile test
%endif

%install
%mvn_install

# Extract the binary tarball
tar -C %{name}-assembly/target -zxf %{name}-assembly/target/%{name}-%{version}-bin.tar.gz

install -d -m 0755 %{buildroot}/%{_bindir}
install -d -m 0755 %{buildroot}/%{_datadir}/%{name}/bin
install -d -m 0755 %{buildroot}/%{_datadir}/%{name}/lib
install -d -m 0755 %{buildroot}/%{_datadir}/%{name}/%{name}-webapps
install -d -m 0755 %{buildroot}/%{_libdir}/%{name}
install -d -m 0755 %{buildroot}/%{_sysconfdir}/%{name}
install -d -m 0755 %{buildroot}/%{_sysconfdir}/logrotate.d
install -d -m 0755 %{buildroot}/%{_tmpfilesdir}
install -d -m 0755 %{buildroot}/%{_unitdir}
install -d -m 0755 %{buildroot}/%{_var}/cache/%{name}
install -d -m 0755 %{buildroot}/%{_sharedstatedir}/%{name}/zookeeper
install -d -m 0755 %{buildroot}/%{_var}/log/%{name}
install -d -m 0755 %{buildroot}/%{_var}/run/%{name}

pushd %{name}-assembly/target/%{name}-%{version}
  # Binaries
  cp -arf bin/* %{buildroot}/%{_datadir}/%{name}/bin
  rm -f %{buildroot}/%{_datadir}/%{name}/bin/*.cmd
  pushd %{buildroot}/%{_datadir}/%{name}/bin
    # Create symlinks for commands in _bindir
    for f in `ls | grep -v \\.rb`
    do
      if [ -f $f ]
      then
        %{__ln_s} %{_datadir}/%{name}/bin/$f %{buildroot}/%{_bindir}
      fi
    done
  popd
  # Remove symlinks from files that aren't commands but are includes
  pushd %{buildroot}/%{_bindir}
    rm -f %{name}-common %{name}-config
  popd

  # Configuration
  install -m 0644 conf/* %{buildroot}/%{_sysconfdir}/%{name}
  rm -f %{buildroot}/%{_sysconfdir}/%{name}/*.cmd
  install -m 0644 %{SOURCE2} %{buildroot}/%{_sysconfdir}/%{name}

  # Modify hbase-env.sh to point to the correct location for JAVA_HOME
  sed -i "s|#\s*export JAVA_HOME.*|export JAVA_HOME=/usr/lib/jvm/jre|" %{buildroot}/%{_sysconfdir}/%{name}/%{name}-env.sh

  # Modify hbase-env.sh to point to the correct location for pid creation
  sed -i "s|#\s*export HBASE_PID_DIR.*|export HBASE_PID_DIR=/var/run/hbase|" %{buildroot}/%{_sysconfdir}/%{name}/%{name}-env.sh

  # Modify hbase-env.sh to point to the correct location for log files
  sed -i "s|#\s*export HBASE_LOG_DIR.*|export HBASE_LOG_DIR=/var/log/hbase|" %{buildroot}/%{_sysconfdir}/%{name}/%{name}-env.sh

  # Link the hdfs-site.xml into the config directory to pick up any HDFS
  # client configuration
  %{__ln_s} %{_sysconfdir}/hadoop/hdfs-site.xml %{buildroot}/%{_sysconfdir}/%{name}

  # Webapps
  cp -arp %{name}-webapps/* %{buildroot}/%{_datadir}/%{name}/%{name}-webapps

  # Dependency jars
  install lib/*.jar %{buildroot}/%{_datadir}/%{name}/lib
  rm -f %{buildroot}/%{_datadir}/%{name}/lib/tools-*.jar
  rm -f %{buildroot}/%{_datadir}/%{name}/lib/%{name}*-tests.jar
  rm -f %{buildroot}/%{_datadir}/%{name}/lib/%{name}-testing-util-*.jar
  rm -f %{buildroot}/%{_datadir}/%{name}/lib/tomcat-*.jar
  rm -f %{buildroot}/%{_datadir}/%{name}/lib/servlet-api-*.jar
  xmvn-subst %{buildroot}/%{_datadir}/%{name}/lib
  pushd %{buildroot}/%{_datadir}/%{name}/lib
    # Replace jar files with symlinks for all jars from the build
    for f in `ls hbase*`
    do
      n=`echo $f | sed "s/-%{version}//"`
      rm -f $f
      %{__ln_s} %{_javadir}/%{name}/$n $f
    done
  popd

  # jruby bits
  cp -arf lib/ruby %{buildroot}/%{_datadir}/%{name}/lib

%if 0
  # Native libraries
  cp -arf lib/native/* %{buildroot}/%{_libdir}/%{name}
%endif
popd

pushd %{buildroot}/%{_datadir}/%{name}
  %{__ln_s} %{_sysconfdir}/%{name} conf
  %{__ln_s} %{_libdir}/%{name} lib/native
  %{__ln_s} %{_var}/log/%{name} logs
  %{__ln_s} %{_var}/run/%{name} pids
popd

# Add jars to the classpath for hbase shell
echo "export HBASE_CLASSPATH_PREFIX=$(build-classpath objectweb-asm/asm objectweb-asm/asm-commons jnr-posix jnr-constants joni jruby bytelist jcodings jnr-ffi joda-time jline jansi invokebinder):\$HBASE_CLASSPATH" > %{buildroot}/%{_sysconfdir}/%{name}/%{name}-env-shell.sh
echo "export JRUBY_HOME=/usr/share/jruby" >> %{buildroot}/%{_sysconfdir}/%{name}/%{name}-env-shell.sh

# Ensure /var/run directory is recreated on boot
echo "d %{_var}/run/%{name} 0775 hbase hbase -" > %{buildroot}/%{_tmpfilesdir}/%{name}.conf

# logrotate config
install -m 0644 %{SOURCE1} %{buildroot}/%{_sysconfdir}/logrotate.d/%{name}

# systemd configuration
for service in %{services}
do
  s=`echo $service | cut -d'-' -f 2- | cut -d'.' -f 1`
  sed -e "s|DAEMON|$s|g" %{SOURCE3} > %{buildroot}/%{_unitdir}/%{name}-$s.service
done

%pretrans -p <lua>
path = "%{_datadir}/%{name}/%{name}-webapps"
st = posix.stat(path)
if st and st.type == "link" then
  os.remove(path)
end

%pre
getent group hbase >/dev/null || /usr/sbin/groupadd -r hbase
getent passwd hbase > /dev/null || /usr/sbin/useradd -c "Apache HBase" -s /sbin/nologin -g hbase -r -d %{_sharedstatedir}/%{name} hbase

%preun
%systemd_preun %{services}

%post
# Change the home directory for the hbase user
if [[ `getent passwd hbase | cut -d: -f 6` != "%{_sharedstatedir}/%{name}" ]]
then
  /usr/sbin/usermod -d %{_sharedstatedir}/%{name} hbase
fi

if [ $1 -gt 1 ]
then
  if [ -d %{_var}/cache/%{name}/zookeeper ] && [ ! -L %{_var}/cache/%{name}/zookeeper ]
  then
    # Move the existing zookeeper data to the new location
    mv -f %{_var}/cache/%{name}/zookeeper/* %{_sharedstatedir}/%{name}/zookeeper
  fi

  if [ -d %{_var}/cache/%{name}/%{name} ] && [ ! -L %{_var}/cache/%{name}/%{name} ]
  then
    # Move the existing hbase data to the new location
    mv -f %{_var}/cache/%{name}/%{name}/* %{_var}/cache/%{name}
  fi
fi
%systemd_post %{services}

%postun
%systemd_postun_with_restart %{services}

if [ $1 -lt 1 ]
then
  # Remove compatibility symlinks
  rm -f %{_var}/cache/%{name}/%{name}
  rm -f %{_var}/cache/%{name}/zookeeper
fi

%posttrans
# Create symlinks to the new locations for zookeeper and hbase data in case
# the user changed the configuration file and the new one isn't in place to
# point to the correct location
if [ -d %{_var}/cache/%{name}/zookeeper ]
then
  rm -rf %{_var}/cache/%{name}/zookeeper
fi
if [ ! -e %{_var}/cache/%{name}/zookeeper ]
then
  %{__ln_s} %{_sharedstatedir}/%{name}/zookeeper %{_var}/cache/%{name}
fi

if [ -d %{_var}/cache/%{name}/%{name} ]
then
  rm -rf %{_var}/cache/%{name}/%{name}
fi
if [ ! -e %{_var}/cache/%{name}/%{name} ]
then
  %{__ln_s} %{_var}/cache/%{name} %{_var}/cache/%{name}
fi

%files -f .mfiles
%doc LICENSE.txt NOTICE.txt README.txt CHANGES.txt
%exclude %{_datadir}/%{name}/lib/native
%{_bindir}/*
%{_datadir}/%{name}
%dir %{_javadir}/%{name}
%attr(-,hbase,hbase) %{_sharedstatedir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%{_tmpfilesdir}/%{name}.conf
%{_unitdir}/%{name}-*.service
%attr(0755,hbase,hbase) %dir %{_var}/cache/%{name}
%attr(0755,hbase,hbase) %dir %{_var}/log/%{name}
%attr(0755,hbase,hbase) %dir %{_var}/run/%{name}

%if %{package_native}
%files native
%{_datadir}/%{name}/lib/native
%{_libdir}/%{name}
%endif

%if %{with javadoc}
%files -f .mfiles-javadoc javadoc
%doc LICENSE.txt NOTICE.txt
%endif

%files -f .mfiles-%{name}-tests tests

%changelog
* Fri Mar 28 2014 Michael Simacek <msimacek@redhat.com> - 0.96.1.1-4
- Use Requires: java-headless rebuild (#1067528)

* Mon Jan 27 2014 Robert Rati <rrati@redhat> - 0.96.1.1-3
- Added option to enable running the test suite

* Mon Jan 13 2014 Robert Rati <rrati@redhat> - 0.96.1.1-2
- Made sure the shell classpath mods are prefixed to the classpath

* Mon Jan 6 2014 Robert Rati <rrati@redhat> - 0.96.1.1-1
- Update to upstream 0.96.1.1
- Properly conditionalize packaging native bits
- Changed findbugs:annotations to use new gid:aid

* Fri Dec 20 2013 Robert Rati <rrati@redhat> - 0.96.0-1
- Initial packaging
