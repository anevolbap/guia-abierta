# Datos y licencias

Todo el proyecto es abierto. El código va con licencia MIT (ver `LICENSE`). Los
datos de entrada y el folleto generado llevan licencias abiertas, todas con
obligación de atribución (ninguna copyleft que afecte al folleto impreso).

| Capa | Fuente | Licencia |
|------|--------|----------|
| Recorridos de colectivos AMBA | Ministerio de Transporte (datos.transporte.gob.ar) | CC-BY 4.0 |
| Subte GTFS | GCBA (data.buenosaires.gob.ar) | CC-BY 2.5 AR |
| Callejero (calles) | GCBA | CC-BY 2.5 AR |
| Barrios | GCBA | CC-BY 2.5 AR |
| Manzanas catastrales | GCBA | CC-BY 2.5 AR |
| Puntos de interés (POIs) | OpenStreetMap | ODbL 1.0 |

Notas:

- CC-BY (4.0 y 2.5 AR) y ODbL son licencias abiertas. La única condición real
  para este uso es **atribuir** la fuente. Está hecho en la tapa y en el pie de
  cada página de mapa.
- ODbL tiene "share-alike", pero aplica a *bases de datos derivadas*, no a una
  *obra producida* (un mapa o folleto impreso). Un folleto solo necesita
  atribuir a OpenStreetMap, no relicenciarse bajo ODbL.
- Por eso el folleto generado se puede distribuir libremente manteniendo las
  atribuciones. El código puede ser MIT sin conflicto (OCitySMap, que es AGPL,
  no es dependencia).

Atribución mínima a incluir si redistribuís el folleto:

> Recorridos AMBA (Min. Transporte, CC-BY 4.0) · Subte / Callejero / Barrios /
> Manzanas (GCBA, CC-BY 2.5 AR) · Puntos de interés © OpenStreetMap
> contributors (ODbL).

## Sobre el nombre

"Guía T" es un nombre comercial de larga data (la guía de bolsillo clásica), así
que conviene **no** usarlo como nombre del proyecto. El nombre por defecto es
**Guía Abierta** (configurable en `config.yaml` → `booklet.title`). Otras
opciones sin conflicto evidente: *Bondiguía*, *Trama* (por la grilla), *Guía
Bondi*, *Mapa Bondi*. "Guía T" se usa solo como referencia descriptiva del
formato, no como marca.
