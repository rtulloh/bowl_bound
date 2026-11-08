# Version information

The current release candidate is **1.0.0**. Python packaging and public display
versions both use **1.0.0**. Its planned immutable Git tag is `v1.0.0`.

`bowl_bound.__version__`, project metadata and API OpenAPI metadata use the
Python form. Frontend package/lock metadata and `bowl_bound.DISPLAY_VERSION`
use the public form. `GET /api/version` returns both as `version` and
`python_version`, without filesystem paths or machine details. For a local
default server, open <http://127.0.0.1:8001/api/version>. Include `version`
when reporting a problem. Standalone launcher version reporting will use the
same public identity.

Application version numbers are not save compatibility profiles. The release retains
`bowl-bound-m33-v1` and the existing save schema. Generated charts have changed
content identities; older saves may require the original chart catalog. Keep
copies of saves and the earlier version before upgrading. Version 1.0.0 does not
certify historical chart accuracy. Never delete/reuse an already published tag.
