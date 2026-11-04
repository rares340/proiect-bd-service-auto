drop table if exists recomandare_diagnoza cascade;
drop table if exists inspectie_itp cascade;
drop table if exists piesa_comanda cascade;
drop table if exists lucrare_efectuata cascade;
drop table if exists programare cascade;
drop table if exists comanda_reparatie cascade;
drop table if exists piesa cascade;
drop table if exists furnizor cascade;
drop table if exists lucrare_catalog cascade;
drop table if exists vehicul cascade;
drop table if exists angajat cascade;
drop table if exists client cascade;
drop table if exists utilizator cascade;

create table client(
    id_client integer generated always as identity primary key,
    nume varchar(50) not null,
    prenume varchar(50) not null,
    telefon varchar(15) not null,
    email varchar(100)
);

create table angajat(
    id_angajat integer generated always as identity primary key,
    nume varchar(100) not null,
    functie varchar(10) not null check(functie in('MECANIC','OPERATOR','INSPECTOR')),
    tarif_orar numeric(8,2) check(tarif_orar is null or tarif_orar>=0)
);

create table utilizator (
    id_utilizator integer generated always as identity primary key,
    nume_utilizator varchar(50) not null unique,
    parola varchar(255) not null,
    rol varchar(20) not null check (rol in ('ADMINISTRATOR', 'OPERATOR', 'INSPECTOR')),
    activ boolean not null default true,
    data_creare timestamp not null default now(),
    id_angajat integer unique references angajat(id_angajat)
);

create table vehicul(
    id_vehicul integer generated always as identity primary key,
    serie_sasiu char(17) not null unique check(length(serie_sasiu)=17),
    nr_inmatriculare varchar(10) not null unique,
    marca varchar(30) not null,
    model varchar(40) not null,
    motorizare varchar(30),
    combustibil varchar(10) not null check(combustibil in('BENZINA','MOTORINA','GPL','HIBRID','ELECTRIC')),
    an_fabricatie smallint not null check(an_fabricatie between 1950 and 2100),
    norma_poluare varchar(10) check(norma_poluare is null or norma_poluare in('Euro 1','Euro 2','Euro 3','Euro 4','Euro 5','Euro 6')),
    id_client integer not null references client(id_client) 
);

create table lucrare_catalog(
    id_lucrare_catalog integer generated always as identity primary key,
    denumire varchar(100) not null unique,
    durata_ore numeric(4,2) not null check(durata_ore>0)
);

create table furnizor(
    id_furnizor integer generated always as identity primary key,
    denumire varchar(100) not null,
    cui varchar(12) not null unique,
    telefon varchar(15)
);

create table piesa(
    id_piesa integer generated always as identity primary key,
    cod varchar(30) not null unique,
    denumire varchar(100) not null,
    categorie varchar(30) not null,
    pret_vanzare numeric(10,2) not null check(pret_vanzare>=0),
    stoc_curent integer not null default 0 check(stoc_curent>=0),
    prag_minim integer not null default 0 check(prag_minim>=0),
    id_furnizor integer not null references furnizor(id_furnizor) 
);

create table comanda_reparatie(
    id_comanda integer generated always as identity primary key,
    data_intrare date not null default current_date,
    data_predare date check(data_predare is null or data_predare>=data_intrare),
    km_intrare integer not null check(km_intrare>=0),
    status varchar(12) not null default 'DESCHISA' check(status in('DESCHISA','IN_LUCRU','FINALIZATA','PREDATA')),
    reclamatie text,
    id_vehicul integer not null references vehicul(id_vehicul),
    id_operator integer not null references angajat(id_angajat) 
);

create table programare(
    id_programare integer generated always as identity primary key,
    data_programare timestamp not null,
    durata_estimata_ore numeric(4,2) not null check(durata_estimata_ore>0),
    descriere_problema text,
    status varchar(12) not null default 'PROGRAMATA' check(status in('PROGRAMATA','ONORATA','ANULATA','NEPREZENTAT')),
    id_vehicul integer not null references vehicul(id_vehicul),
    id_lucrare_catalog integer not null references lucrare_catalog(id_lucrare_catalog),
    id_comanda integer unique references comanda_reparatie(id_comanda)
);

create table lucrare_efectuata(
    id_lucrare_efectuata integer generated always as identity primary key,
    post_lucru varchar(30),
    ore_lucrate numeric(5,2) not null default 0 check(ore_lucrate>=0),
    tarif_orar_aplicat numeric(8,2) not null check(tarif_orar_aplicat>=0),
    id_comanda integer not null references comanda_reparatie(id_comanda),
    id_mecanic integer not null references angajat(id_angajat),
    id_lucrare_catalog integer not null references lucrare_catalog(id_lucrare_catalog)
);

create table piesa_comanda(
    id_comanda integer not null references comanda_reparatie(id_comanda),
    id_piesa integer not null references piesa(id_piesa),
    cantitate integer not null check(cantitate>0),
    pret_unitar_aplicat numeric(10,2) not null check(pret_unitar_aplicat>=0),
    primary key(id_comanda,id_piesa)
);

create table inspectie_itp(
    id_inspectie integer generated always as identity primary key,
    data_inspectie date not null default current_date,
    km integer not null check(km>=0),
    emisii_co numeric(5,3) check(emisii_co is null or emisii_co>=0),
    eficienta_franare numeric(5,2) check(eficienta_franare is null or eficienta_franare between 0 and 100),
    convergenta numeric(5,2),
    rezultat varchar(10) not null check(rezultat in('ADMIS','RESPINS')),
    data_expirare date check((rezultat='ADMIS' and data_expirare is not null and data_expirare>data_inspectie) or (rezultat='RESPINS' and data_expirare is null)),
    id_vehicul integer not null references vehicul(id_vehicul),
    id_inspector integer not null references angajat(id_angajat)
);

create table recomandare_diagnoza(
    id_recomandare integer generated always as identity primary key,
    categorie varchar(30) not null,
    scor_risc numeric(4,3) not null check(scor_risc between 0 and 1),
    algoritm varchar(40) not null,
    data_generare timestamp not null default now(),
    id_vehicul integer not null references vehicul(id_vehicul)
);

create index ix_vehicul_client on vehicul(id_client);
create index ix_utilizator_angajat on utilizator(id_angajat);
create index ix_comanda_vehicul on comanda_reparatie(id_vehicul);
create index ix_comanda_data on comanda_reparatie(data_intrare);
create index ix_programare_data on programare(data_programare);
create index ix_programare_vehicul on programare(id_vehicul);
create index ix_lucrare_comanda on lucrare_efectuata(id_comanda);
create index ix_lucrare_mecanic on lucrare_efectuata(id_mecanic);
create index ix_piesa_categorie on piesa(categorie);
create index ix_piesa_furnizor on piesa(id_furnizor);
create index ix_pc_piesa on piesa_comanda(id_piesa);
create index ix_itp_vehicul on inspectie_itp(id_vehicul);
create index ix_itp_expirare on inspectie_itp(data_expirare);
create index ix_recomandare_vehicul on recomandare_diagnoza(id_vehicul);