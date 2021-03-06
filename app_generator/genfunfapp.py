#!/usr/bin/env python
# 
# Funf: Open Sensing Framework
# Copyright (C) 2010-2011 Nadav Aharony, Wei Pan, Alex Pentland.
# Acknowledgments: Alan Gardner
# Contact: nadav@media.mit.edu
# 
# This file is part of Funf.
# 
# Funf is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
# 
# Funf is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with Funf. If not, see <http://www.gnu.org/licenses/>.
# 
from subprocess import check_call, CalledProcessError
import shutil
import tempfile
import os.path
import simplejson as json
import string
import re
import inspect
import random

keystorepass = 'inabox'
keystorename = 'release-key.keystore'
keyalias = 'release'
_unknown = "Unknown"

_all_permisssions = '''
    <!-- Location probe, Cell probe -->
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/> 
    
    <!-- Location probe -->
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>   
    
    <!-- Wifi and Hardware Info probes -->
    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/> 
    
     <!-- Wifi probe -->
    <uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/> 
    
    <!-- Bluetooth probe -->
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN"/> 
    
    <!-- Bluetooth and Hardware Info probes -->
    <uses-permission android:name="android.permission.BLUETOOTH"/> 
    
    <!-- Running applications probe -->
    <uses-permission android:name="android.permission.GET_TASKS"/> 
    
    <!-- Browser probes -->
    <uses-permission android:name="com.android.browser.permission.READ_HISTORY_BOOKMARKS" />
    
    <!-- Call Log and Contact probes -->
    <uses-permission android:name="android.permission.READ_CONTACTS" />
    
    <!--  SMS Probe -->
    <uses-permission android:name="android.permission.READ_SMS" />
    
    <!-- Running applications probe -->
    <uses-permission android:name="android.permission.GET_TASKS"/> 
    
    <!-- Running Audio features probe -->
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    
    <!-- DatabaseService, Archive service (unique ids) -->
    <uses-permission android:name="android.permission.READ_PHONE_STATE" />

    <!-- Accounts probe -->
    <uses-permission android:name="android.permission.GET_ACCOUNTS"/> 

    <!-- Call logs -->
    <uses-permission android:name="android.permission.READ_CALL_LOG"/>
    
    <!-- User Study Notification probe -->
    <uses-permission android:name="android.permission.VIBRATE"/>
'''

def gen_signing_key(directory, password=keystorepass, name=_unknown, organization=_unknown, organizational_unit=_unknown, city=_unknown, state_or_region=_unknown, country=_unknown):
    if not os.path.exists(directory):
        os.mkdir(directory)
    if not os.path.isdir(directory):
        return None
    
    
    dname = "CN=%s, OU=%s, O=%s, L=%s, ST=%s, C=%s" % (name, organizational_unit, organization, city, state_or_region, country)
    keystore_path = os.path.join(directory, keystorename)
    try:
        # keytool -genkey -v -keystore release-key.keystore -alias release -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Alan Gardner, OU=Human Dynamics, O=MIT Media Lab, L=Cambridge, ST=Massachusetts, C=US" -storepass inabox -keypass inabox
        check_call(['keytool', '-genkey', '-v', '-keystore', keystore_path, '-alias', keyalias, '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-dname', dname, '-storepass', password, '-keypass', password])
        return keystore_path
    except CalledProcessError as e:
        return None

script_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
android_app_template = os.path.join(script_dir, 'android_app_template') 
dir_template = os.path.join(script_dir, 'dir_template')
invalid_filename_chars = r'[^A-Za-z0-9_ \-\.\(\)]*'
invalid_id_chars = r'[^A-Za-z0-9_]*'
DROPBOX_APP_KEY = os.environ['DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['DROPBOX_APP_SECRET']

def generate(dir_path, user_id, dropbox_token, dropbox_token_secret, name, description, contact_email, funf_conf):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    dir_filename = re.sub(invalid_filename_chars, '', name).strip()
    destination_dir = os.path.join(dir_path, dir_filename)
    if os.path.exists(destination_dir):
        raise Exception("Directory already exists")
    
    working_dir = tempfile.mkdtemp(prefix="funfinabox-")
    app_id = 'f_%s_%s' % (str(user_id), re.sub(invalid_id_chars, '', name.strip().lower().replace(' ', '_')))
    
    
    study_dir = os.path.join(working_dir, dir_filename)
    android_app_dir = os.path.join(working_dir, "android_app")
    
    # Copy directory structure template
    shutil.copytree(dir_template, study_dir)
    config_dir = os.path.join(study_dir, 'config')
    keystore_path = gen_signing_key(config_dir)
    
    # Create encryption password/key
    encryption_password = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(12))
    with open(os.path.join(config_dir, 'encryption_password.txt'), 'w') as file:
        file.write(encryption_password)


    funf_config_obj = json.loads(funf_conf)
    # Add password to funf config
    funf_config_obj['archive'] = {
        'name': funf_config_obj['name'],
        'password': encryption_password
    }
    funf_conf = json.dumps(funf_config_obj)
    
    # Create Funf Config
    with open(os.path.join(config_dir, 'funf_config.json'), 'w') as file:
        file.write(funf_conf)
    
    # Create App Config (May later roll into funf config)
    app_config = {'id': app_id ,'name': name, 'description': description, 'contact_email': contact_email }
    with open(os.path.join(config_dir, 'app_config.json'), 'w') as file:
        file.write(json.dumps(app_config))
    
    # Create android app
    shutil.copytree(android_app_template, android_app_dir)
    shutil.copy(keystore_path, android_app_dir)
    
    ## Create inabox.properties
    permissions = _all_permisssions.replace('\n', '') # TODO: calculate only necessary permissions
    
    # Quotes escaped for java properties file, so that resources compile
    inabox_properties = {'inabox.app.name': dir_filename.replace("'", r"\\'").replace('"', r'\\"'),
                         'inabox.app.id': app_id,
                         'inabox.app.description': description.replace("'", r"\\'").replace('"', r'\\"'),
                         'inabox.app.email': contact_email,
                         'inabox.app.config': funf_conf.replace('\n', '').replace("'", r"\\'").replace('"', r'\\"'),
                         'inabox.app.permissions': permissions,
                         'inabox.app.password': encryption_password,
                         'inabox.dropbox.appkey': DROPBOX_APP_KEY,
                         'inabox.dropbox.appsecret': DROPBOX_APP_SECRET,
                         'inabox.dropbox.token': dropbox_token,
                         'inabox.dropbox.tokensecret': dropbox_token_secret,
                         }
    #print inabox_properties
    
    with open(os.path.join(android_app_dir, 'inabox.properties'), 'w') as file:
        file.writelines(["%s = %s\n" % (key, value) for key, value in inabox_properties.iteritems()])
    
    try:
        check_call(['ant','clean', 'customize', 'release'], cwd=android_app_dir)
    except CalledProcessError as e:
        return None
    
    shutil.copy(os.path.join(android_app_dir, 'bin', 'Info-release.apk'), 
                os.path.join(study_dir, dir_filename.replace(" ", "-") + '-release.apk'))
    
    
    shutil.copytree(study_dir, destination_dir)
    
    # Cleanup
    shutil.rmtree(working_dir)
    
    return destination_dir
