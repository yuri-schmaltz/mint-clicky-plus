#!/bin/bash
set -e

APP_NAME="clicky"
VERSION="1.1.0"
OUTPUT_DIR="releases"

mkdir -p $OUTPUT_DIR

echo "📦 Starting packaging for $APP_NAME v$VERSION..."

# We use fpm (Effing Package Management) inside Docker to build deb and rpm
# Benefits: No need to install ruby/rpm/fpm locally, results are consistent.

PACKAGER_IMAGE="ghcr.io/linuxmint/fpm:latest" # Using a known good FPM image if available, or just ruby
# If we don't have a specific image, we use ruby and install fpm on the fly
IMAGE="ruby:3.1-slim"

docker run --rm -v "$(pwd):/src" -w /src $IMAGE bash -c "
    apt-get update && apt-get install -y build-essential binutils rpm
    gem install --no-document fpm
    
    # Generate DEB
    fpm -s dir -t deb \
        -n $APP_NAME -v $VERSION \
        --description 'Desktop screenshot application with advanced editor' \
        --maintainer 'Antigravity AI <antigravity@google.com>' \
        --architecture all \
        --depends 'python3' --depends 'python3-gi' --depends 'python3-gi-cairo' \
        --depends 'gir1.2-gtk-3.0' --depends 'gir1.2-gsound-1.0' --depends 'gir1.2-xapp-1.0' \
        --depends 'python3-setproctitle' --depends 'xapps-common' \
        usr/

    # Generate RPM
    fpm -s dir -t rpm \
        -n $APP_NAME -v $VERSION \
        --description 'Desktop screenshot application with advanced editor' \
        --maintainer 'Antigravity AI <antigravity@google.com>' \
        --architecture noarch \
        --depends 'python3' --depends 'python3-gobject' --depends 'python3-cairo' \
        --depends 'gtk3' --depends 'libgsound' \
        usr/

    mv *.deb *.rpm $OUTPUT_DIR/
"

echo "✅ Packaging complete. Files are in $OUTPUT_DIR/"
ls -lh $OUTPUT_DIR/
