# tools/certs — pinned trust anchors for capture

A capture is only evidence if the fetch that produced it was authenticated. Most
agencies serve a complete certificate chain and the system trust store handles
them; nothing here applies to those, and nothing here is used unless a recipe
asks for it by name.

Some do not. `www.ksde.gov` presents its leaf certificate without the
intermediate that signs it, so a correct client cannot build a path to any root
and the fetch fails with "unable to get local issuer certificate". Browsers hide
this by caching intermediates from earlier sites or fetching them through the
certificate's AIA extension; `curl` does neither. That is why the Kansas packet
carried a capture gap from 2026-08-25 to 2026-08-29 recording ksde.gov as
unfetchable, and why five of its six sources had to be downloaded by hand.

The wrong fix is `--insecure`. It does not repair the chain; it stops checking,
which for a project whose whole claim is that its quotations came from the
agency's own server is the one thing that must not happen quietly.

The right fix is to supply the missing link. A bundle here holds a root and the
intermediates needed under it, and a recipe naming it gets `curl --cacert
<bundle>` — full verification, against these anchors instead of the system
store. Pinning narrows trust rather than widening it: a capture taken this way
was served by a certificate chaining to exactly the root named below, and
nothing else in the system store could have satisfied it.

## digicert-global-root-g2.pem

- DigiCert Global Root G2
  `CB:3C:CB:B7:60:31:E5:E0:13:8F:8D:D3:9A:23:F9:DE:47:FF:C3:5E:43:C1:14:4C:EA:27:D4:6A:5A:B1:CB:5F`
- DigiCert Global G2 TLS RSA SHA256 2020 CA1 (intermediate, expires 2031-03-29)
  `C8:02:5F:9F:C6:5F:DF:C9:5B:3C:A8:CC:78:67:B9:A5:87:B5:27:79:73:95:79:17:46:3F:C8:13:D0:B6:25:A9`

Both were retrieved 2026-08-29 from `http://cacerts.digicert.com/`, the address
published in the CA Issuers extension of ksde.gov's own certificate. Verify
either against DigiCert's published fingerprints before trusting this file; the
fingerprints above are here so that a reviewer can, not so that they need not.

Used by: kansas.

When the intermediate expires, a capture will start failing with a verification
error rather than silently succeeding on a weaker path. That is the correct
failure and it should be fixed by replacing the bundle, not by removing the
pin.
