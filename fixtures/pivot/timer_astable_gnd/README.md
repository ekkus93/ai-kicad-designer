# timer_astable_gnd

Copy of `fixtures/m2b/timer_astable.json` with the return net renamed from `REF` to
`GND` (owner direction 2026-10-31), so the drawn ground symbol reads GND. Every exact
`"REF"` net reference was renamed: `nets[4].id`, `relationships[0].reference`,
`relationships[1].reference`, `relationships[2].return` and `power_assertions[1].net`;
`id` is `timer_astable_gnd`. The M2b original is unchanged because legacy M2c1 tests use it.
