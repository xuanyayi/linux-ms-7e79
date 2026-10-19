# CachyOS source signing keys

These are public keys, pinned to the two fingerprints listed in the official
`CachyOS/linux-cachyos` server PKGBUILD. The updater accepts no other signer and
does not retrieve keys automatically.

| File | Primary fingerprint | Publisher |
| --- | --- | --- |
| `ptr1337.asc` | `E8B9AA39F054E30E8290D492C3C4820857F654FE` | Peter Jung |
| `naim.asc` | `E18447AC260021D31F3FF6C4C8A2A4774B8B63C4` | Eric Naim |

The key material was retrieved on 2026-10-19 from
`https://keys.openpgp.org/vks/v1/by-fingerprint/<fingerprint>` and checked against
the fingerprints above. Refreshing an expired key or changing an approved signer
is an explicit repository change. Never work around a verification failure by
disabling signature verification.
