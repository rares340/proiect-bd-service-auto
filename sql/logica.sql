
-- ---------------------------------------------------------------------
-- 0. Curatare (permite re-rularea fisierului)
-- ---------------------------------------------------------------------
drop view if exists v_deviz cascade;
drop view if exists v_comanda_detaliu cascade;
drop view if exists v_piese_sub_prag cascade;
drop view if exists v_itp_ultima cascade;
drop view if exists v_istoric_vehicul cascade;
drop view if exists v_date_ai cascade;

drop function  if exists fn_adauga_piesa_comanda(integer, integer, integer);
drop function  if exists fn_raport_productivitate(date, date);
drop function  if exists fn_raport_profitabilitate(date, date);
drop function  if exists fn_piese_fara_rulaj(integer);
drop procedure if exists sp_deschide_comanda_din_programare(integer, integer, integer, integer);


-- =====================================================================
-- 1. FUNCTII AJUTATOARE
-- =====================================================================

-- Numarul de elevatoare (posturi de lucru) ale service-ului. 
create or replace function fn_nr_elevatoare() returns integer
language sql immutable as $$ select 3 $$;


-- Scade stocul unei piese. Cantitate negativa = readauga in stoc.
create or replace function fn_scade_stoc(p_id_piesa integer, p_cantitate integer)
returns void language plpgsql as $$
declare
    v_stoc integer;
    v_den  varchar;
begin
    if p_cantitate = 0 then
        return;
    end if;

    select stoc_curent, denumire into v_stoc, v_den
    from piesa where id_piesa = p_id_piesa
    for update;

    if not found then
        raise exception 'Piesa % nu exista', p_id_piesa;
    end if;

    if p_cantitate > 0 and v_stoc < p_cantitate then
        raise exception 'Stoc insuficient pentru piesa "%": disponibil %, cerut %',
                        v_den, v_stoc, p_cantitate;
    end if;

    update piesa set stoc_curent = stoc_curent - p_cantitate
    where id_piesa = p_id_piesa;
end $$;


-- Data expirarii ITP in functie de vechimea vehiculului (CF13):
--   3 ani la prima inspectie admisa, 2 ani pana la 12 ani vechime, 1 an dupa.
-- Vechimea > 12 ani are prioritate: un vehicul vechi, nou intrat in sistem,
-- nu primeste 3 ani. 
create or replace function fn_expirare_itp(p_id_vehicul integer, p_data date)
returns date language plpgsql stable as $$
declare
    v_an       integer;
    v_vechime  integer;
    v_prima    boolean;
    v_ani      integer;
begin
    select an_fabricatie into v_an from vehicul where id_vehicul = p_id_vehicul;
    if not found then
        raise exception 'Vehiculul % nu exista', p_id_vehicul;
    end if;

    v_vechime := extract(year from p_data)::integer - v_an;

    v_prima := not exists (
        select 1 from inspectie_itp
        where id_vehicul = p_id_vehicul
          and rezultat = 'ADMIS'
          and data_inspectie < p_data
    );

    if v_vechime > 12 then
        v_ani := 1;
    elsif v_prima then
        v_ani := 3;
    else
        v_ani := 2;
    end if;

    return (p_data + make_interval(years => v_ani))::date;
end $$;


-- =====================================================================
-- 2. TRIGGERE
-- =====================================================================

-- ---- 2.1 Stocul se actualizeaza automat cand se modifica piesa_comanda (CF7)
create or replace function trg_fn_pc_stoc() returns trigger
language plpgsql as $$
begin
    if tg_op = 'INSERT' then
        perform fn_scade_stoc(new.id_piesa, new.cantitate);
    elsif tg_op = 'UPDATE' then
        if new.id_piesa = old.id_piesa then
            perform fn_scade_stoc(new.id_piesa, new.cantitate - old.cantitate);
        else
            perform fn_scade_stoc(old.id_piesa, -old.cantitate);
            perform fn_scade_stoc(new.id_piesa, new.cantitate);
        end if;
    else  -- DELETE
        perform fn_scade_stoc(old.id_piesa, -old.cantitate);
    end if;
    return null;
end $$;

drop trigger if exists trg_piesa_comanda_stoc on piesa_comanda;
create trigger trg_piesa_comanda_stoc
    after insert or update or delete on piesa_comanda
    for each row execute function trg_fn_pc_stoc();


-- ---- 2.2 Pretul piesei se ia din catalog la inserare si ramane inghetat (CNF3)
create or replace function trg_fn_pc_pret() returns trigger
language plpgsql as $$
declare
    v_pret numeric;
begin
    if tg_op = 'INSERT' then
        select pret_vanzare into v_pret from piesa where id_piesa = new.id_piesa;
        if v_pret is null then
            raise exception 'Piesa % nu exista', new.id_piesa;
        end if;
        new.pret_unitar_aplicat := v_pret;
    elsif new.pret_unitar_aplicat is distinct from old.pret_unitar_aplicat then
        raise exception 'Pretul unitar aplicat nu mai poate fi modificat dupa utilizare';
    end if;
    return new;
end $$;

drop trigger if exists trg_piesa_comanda_pret on piesa_comanda;
create trigger trg_piesa_comanda_pret
    before insert or update on piesa_comanda
    for each row execute function trg_fn_pc_pret();


-- ---- 2.3 Tariful mecanicului se copiaza la inserare si ramane inghetat (CF6, CNF3)
create or replace function trg_fn_lucrare_tarif() returns trigger
language plpgsql as $$
declare
    v_tarif numeric;
begin
    if tg_op = 'INSERT' then
        select tarif_orar into v_tarif from angajat where id_angajat = new.id_mecanic;
        if v_tarif is null then
            raise exception 'Mecanicul % nu exista sau nu are tarif orar definit', new.id_mecanic;
        end if;
        new.tarif_orar_aplicat := v_tarif;
    elsif new.tarif_orar_aplicat is distinct from old.tarif_orar_aplicat then
        raise exception 'Tariful orar aplicat nu mai poate fi modificat';
    end if;
    return new;
end $$;

drop trigger if exists trg_lucrare_tarif on lucrare_efectuata;
create trigger trg_lucrare_tarif
    before insert or update on lucrare_efectuata
    for each row execute function trg_fn_lucrare_tarif();


-- ---- 2.4 O comanda inchisa nu mai primeste lucrari sau piese
create or replace function trg_fn_comanda_modificabila() returns trigger
language plpgsql as $$
declare
    v_id     integer;
    v_status varchar;
begin
    if tg_op = 'DELETE' then
        v_id := old.id_comanda;
    else
        v_id := new.id_comanda;
    end if;

    select status into v_status from comanda_reparatie where id_comanda = v_id;

    if v_status in ('FINALIZATA', 'PREDATA') then
        raise exception 'Comanda % este % si nu mai poate fi modificata', v_id, v_status;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end $$;

drop trigger if exists trg_piesa_comanda_deschisa on piesa_comanda;
create trigger trg_piesa_comanda_deschisa
    before insert or update or delete on piesa_comanda
    for each row execute function trg_fn_comanda_modificabila();

drop trigger if exists trg_lucrare_deschisa on lucrare_efectuata;
create trigger trg_lucrare_deschisa
    before insert or update or delete on lucrare_efectuata
    for each row execute function trg_fn_comanda_modificabila();


-- 2.5 Tranzitii valide de status pentru comanda (CF5)
create or replace function trg_fn_comanda_status() returns trigger
language plpgsql as $$
begin
    if new.status = old.status then
        return new;
    end if;

    if not (   (old.status = 'DESCHISA'  and new.status = 'IN_LUCRU')
            or (old.status = 'IN_LUCRU'  and new.status = 'FINALIZATA')
            or (old.status = 'FINALIZATA' and new.status = 'PREDATA')) then
        raise exception 'Tranzitie invalida de status: % -> %', old.status, new.status;
    end if;

    if new.status = 'FINALIZATA'
       and not exists (select 1 from lucrare_efectuata where id_comanda = new.id_comanda) then
        raise exception 'Comanda % nu poate fi finalizata fara nicio lucrare efectuata', new.id_comanda;
    end if;

    if new.status = 'PREDATA' and new.data_predare is null then
        new.data_predare := current_date;
    end if;

    return new;
end $$;

drop trigger if exists trg_comanda_status on comanda_reparatie;
create trigger trg_comanda_status
    before update on comanda_reparatie
    for each row execute function trg_fn_comanda_status();


--  2.6 Functia angajatului trebuie sa corespunda rolului actiunii (CNF4)
--  Argumente: numele coloanei cu id-ul angajatului si functia ceruta.
create or replace function trg_fn_verifica_functie() returns trigger
language plpgsql as $$
declare
    v_id      integer;
    v_functie varchar;
begin
    v_id := (to_jsonb(new) ->> tg_argv[0])::integer;
    select functie into v_functie from angajat where id_angajat = v_id;

    if v_functie is distinct from tg_argv[1] then
        raise exception 'Angajatul % trebuie sa aiba functia %, dar are: %',
                        v_id, tg_argv[1], coalesce(v_functie, 'inexistent');
    end if;
    return new;
end $$;

drop trigger if exists trg_comanda_operator on comanda_reparatie;
create trigger trg_comanda_operator
    before insert or update of id_operator on comanda_reparatie
    for each row execute function trg_fn_verifica_functie('id_operator', 'OPERATOR');

drop trigger if exists trg_itp_inspector on inspectie_itp;
create trigger trg_itp_inspector
    before insert or update of id_inspector on inspectie_itp
    for each row execute function trg_fn_verifica_functie('id_inspector', 'INSPECTOR');

drop trigger if exists trg_lucrare_mecanic on lucrare_efectuata;
create trigger trg_lucrare_mecanic
    before insert or update of id_mecanic on lucrare_efectuata
    for each row execute function trg_fn_verifica_functie('id_mecanic', 'MECANIC');


-- 2.7 Programari: nu in trecut, maxim N simultan (N = nr. de elevatoare) (CF4)
create or replace function trg_fn_programare_validare() returns trigger
language plpgsql as $$
declare
    v_sfarsit timestamp;
    v_max     integer;
begin
    -- nu se reverifica daca nu s-a schimbat nimic relevant
    if tg_op = 'UPDATE'
       and new.data_programare = old.data_programare
       and new.durata_estimata_ore = old.durata_estimata_ore
       and new.status = old.status then
        return new;
    end if;

    -- doar programarile active ocupa un elevator
    if new.status <> 'PROGRAMATA' then
        return new;
    end if;

    if new.data_programare < localtimestamp then
        raise exception 'Programarea nu poate fi in trecut (%)', new.data_programare;
    end if;

    -- evita ca doua programari concurente sa treaca amandoua de verificare
    perform pg_advisory_xact_lock(hashtext('programare_elevatoare'));

    v_sfarsit := new.data_programare + new.durata_estimata_ore * interval '1 hour';

    -- verificam momentul de start al noii programari si startul fiecarei
    -- programari existente care incepe in interiorul ei.
    select coalesce(max(x.cnt), 0) into v_max
    from (
        select (
            select count(*) from programare q
            where q.status = 'PROGRAMATA'
              and q.id_programare <> coalesce(new.id_programare, -1)
              and q.data_programare <= t.moment
              and q.data_programare + q.durata_estimata_ore * interval '1 hour' > t.moment
        ) as cnt
        from (
            select new.data_programare as moment
            union
            select p.data_programare
            from programare p
            where p.status = 'PROGRAMATA'
              and p.id_programare <> coalesce(new.id_programare, -1)
              and p.data_programare > new.data_programare
              and p.data_programare < v_sfarsit
        ) t
    ) x;

    if v_max + 1 > fn_nr_elevatoare() then
        raise exception 'Nu exista elevator liber in intervalul % - %: deja % programari simultane (maxim %)',
                        new.data_programare, v_sfarsit, v_max, fn_nr_elevatoare();
    end if;

    return new;
end $$;

drop trigger if exists trg_programare_validare on programare;
create trigger trg_programare_validare
    before insert or update on programare
    for each row execute function trg_fn_programare_validare();


-- 2.8 Programarea devine ONORATA cand i se asociaza o comanda (CF5)
create or replace function trg_fn_programare_onorata() returns trigger
language plpgsql as $$
begin
    if new.id_comanda is not null and old.id_comanda is null then
        new.status := 'ONORATA';
    end if;
    return new;
end $$;

drop trigger if exists trg_programare_onorata on programare;
create trigger trg_programare_onorata
    before update of id_comanda on programare
    for each row execute function trg_fn_programare_onorata();


-- 2.9 Inspectia ITP: ADMIS doar in limite + data expirarii automata (CF12, CF13, CNF2)
create or replace function trg_fn_itp_validare() returns trigger
language plpgsql as $$
declare
    c_max_co       constant numeric := 3.5;   -- limita emisii CO
    c_min_franare  constant numeric := 50;    -- eficienta minima la franare
    v_comb         varchar;
begin
    if new.rezultat = 'ADMIS' then
        select combustibil into v_comb from vehicul where id_vehicul = new.id_vehicul;

        if new.eficienta_franare is null then
            raise exception 'ADMIS necesita eficienta franarii masurata';
        end if;
        if new.eficienta_franare < c_min_franare then
            raise exception 'ITP nu poate fi ADMIS: eficienta franarii % este sub minimul de %',
                            new.eficienta_franare, c_min_franare;
        end if;

        if v_comb is distinct from 'ELECTRIC' then
            if new.emisii_co is null then
                raise exception 'ADMIS necesita emisiile de CO masurate';
            end if;
            if new.emisii_co > c_max_co then
                raise exception 'ITP nu poate fi ADMIS: emisiile CO % depasesc limita de %',
                                new.emisii_co, c_max_co;
            end if;
        end if;

        new.data_expirare := fn_expirare_itp(new.id_vehicul, new.data_inspectie);
    else
        new.data_expirare := null;
    end if;
    return new;
end $$;

drop trigger if exists trg_itp_validare on inspectie_itp;
create trigger trg_itp_validare
    before insert or update on inspectie_itp
    for each row execute function trg_fn_itp_validare();


-- 2.10 Utilizatori: rol coerent cu angajatul, fara stergere (CF2, CNF4)
create or replace function trg_fn_utilizator_validare() returns trigger
language plpgsql as $$
declare
    v_functie varchar;
begin
    if new.rol in ('OPERATOR', 'INSPECTOR') then
        if new.id_angajat is null then
            raise exception 'Rolul % necesita un angajat asociat', new.rol;
        end if;
        select functie into v_functie from angajat where id_angajat = new.id_angajat;
        if v_functie is distinct from new.rol then
            raise exception 'Angajatul asociat are functia %, nu %',
                            coalesce(v_functie, 'inexistent'), new.rol;
        end if;
    end if;
    return new;
end $$;

drop trigger if exists trg_utilizator_validare on utilizator;
create trigger trg_utilizator_validare
    before insert or update on utilizator
    for each row execute function trg_fn_utilizator_validare();


create or replace function trg_fn_utilizator_nu_sterge() returns trigger
language plpgsql as $$
begin
    raise exception 'Utilizatorii nu se sterg, se dezactiveaza (activ = false)';
    return null;
end $$;

drop trigger if exists trg_utilizator_nu_sterge on utilizator;
create trigger trg_utilizator_nu_sterge
    before delete on utilizator
    for each row execute function trg_fn_utilizator_nu_sterge();


-- =====================================================================
-- 3. FUNCTII SI PROCEDURI APELATE DIN APLICATIE
-- =====================================================================

-- 3.1 Adauga o piesa pe comanda; stocul si pretul
-- sunt tratate de triggere. Returneaza stocul ramas si alerta (CF7, CF8).
create or replace function fn_adauga_piesa_comanda(
    p_id_comanda integer, p_id_piesa integer, p_cantitate integer)
returns table(stoc_ramas integer, sub_prag boolean, denumire_piesa varchar)
language plpgsql as $$
begin
    if p_cantitate is null or p_cantitate <= 0 then
        raise exception 'Cantitatea trebuie sa fie mai mare ca 0';
    end if;

    perform 1 from comanda_reparatie where id_comanda = p_id_comanda;
    if not found then
        raise exception 'Comanda % nu exista', p_id_comanda;
    end if;

    perform 1 from piesa where id_piesa = p_id_piesa;
    if not found then
        raise exception 'Piesa % nu exista', p_id_piesa;
    end if;

    -- pretul real este pus de trigger (trg_piesa_comanda_pret)
    insert into piesa_comanda (id_comanda, id_piesa, cantitate, pret_unitar_aplicat)
    values (p_id_comanda, p_id_piesa, p_cantitate, null)
    on conflict (id_comanda, id_piesa)
    do update set cantitate = piesa_comanda.cantitate + excluded.cantitate;

    return query
        select p.stoc_curent, p.stoc_curent <= p.prag_minim, p.denumire
        from piesa p where p.id_piesa = p_id_piesa;
end $$;


-- 3.2 Deschide o comanda pornind de la o programare (CF5)
-- Folosire:  CALL sp_deschide_comanda_din_programare(1, 120000, 2, NULL);
create or replace procedure sp_deschide_comanda_din_programare(
    p_id_programare integer, p_km integer, p_id_operator integer,
    inout p_id_comanda integer default null)
language plpgsql as $$
declare
    v_prog programare%rowtype;
begin
    select * into v_prog from programare
    where id_programare = p_id_programare
    for update;

    if not found then
        raise exception 'Programarea % nu exista', p_id_programare;
    end if;
    if v_prog.status <> 'PROGRAMATA' then
        raise exception 'Programarea % are statusul %, nu poate deschide o comanda',
                        p_id_programare, v_prog.status;
    end if;
    if v_prog.id_comanda is not null then
        raise exception 'Programarea % are deja comanda %', p_id_programare, v_prog.id_comanda;
    end if;

    insert into comanda_reparatie (km_intrare, reclamatie, id_vehicul, id_operator)
    values (p_km, v_prog.descriere_problema, v_prog.id_vehicul, p_id_operator)
    returning id_comanda into p_id_comanda;

    -- trigger-ul trg_programare_onorata seteaza statusul ONORATA
    update programare set id_comanda = p_id_comanda
    where id_programare = p_id_programare;
end $$;


-- 3.3 Raport: productivitatea mecanicilor pe o perioada (CF11)
create or replace function fn_raport_productivitate(p_start date, p_end date)
returns table(
    mecanic_id integer, mecanic_nume varchar, nr_comenzi bigint,
    total_ore numeric, venit_manopera numeric, ore_medii_pe_comanda numeric,
    loc_clasament bigint)
language sql stable as $$
    select a.id_angajat,
           a.nume,
           count(distinct l.id_comanda),
           sum(l.ore_lucrate),
           round(sum(l.ore_lucrate * l.tarif_orar_aplicat), 2),
           round(sum(l.ore_lucrate) / count(distinct l.id_comanda), 2),
           rank() over (order by sum(l.ore_lucrate * l.tarif_orar_aplicat) desc)
    from angajat a
    join lucrare_efectuata l   on l.id_mecanic = a.id_angajat
    join comanda_reparatie c   on c.id_comanda = l.id_comanda
    where a.functie = 'MECANIC'
      and c.data_intrare between p_start and p_end
    group by a.id_angajat, a.nume
    order by 7, 2
$$;


-- 3.4 Raport: profitabilitatea pe tip de lucrare pe o perioada (CF11)
create or replace function fn_raport_profitabilitate(p_start date, p_end date)
returns table(
    lucrare_id integer, lucrare_denumire varchar, nr_lucrari bigint,
    ore_reale numeric, ore_standard numeric, abatere_procent numeric,
    venit_manopera numeric, venit_pe_ora numeric)
language sql stable as $$
    select lc.id_lucrare_catalog,
           lc.denumire,
           count(*),
           sum(l.ore_lucrate),
           count(*) * lc.durata_ore,
           round(100 * (sum(l.ore_lucrate) - count(*) * lc.durata_ore)
                       / (count(*) * lc.durata_ore), 1),
           round(sum(l.ore_lucrate * l.tarif_orar_aplicat), 2),
           round(sum(l.ore_lucrate * l.tarif_orar_aplicat) / sum(l.ore_lucrate), 2)
    from lucrare_catalog lc
    join lucrare_efectuata l  on l.id_lucrare_catalog = lc.id_lucrare_catalog
    join comanda_reparatie c  on c.id_comanda = l.id_comanda
    where c.data_intrare between p_start and p_end
    group by lc.id_lucrare_catalog, lc.denumire, lc.durata_ore
    having sum(l.ore_lucrate) > 0
    order by 7 desc
$$;


-- 3.5 Raport: piese cu stoc care nu au fost folosite in ultimele N luni (CF11)
create or replace function fn_piese_fara_rulaj(p_luni integer default 12)
returns table(
    piesa_id integer, cod_piesa varchar, piesa_denumire varchar, categorie_piesa varchar,
    stoc integer, valoare_stoc numeric, furnizor varchar, ultima_utilizare date)
language sql stable as $$
    select p.id_piesa,
           p.cod,
           p.denumire,
           p.categorie,
           p.stoc_curent,
           round(p.stoc_curent * p.pret_vanzare, 2),
           f.denumire,
           (select max(c.data_intrare)
            from piesa_comanda pc
            join comanda_reparatie c on c.id_comanda = pc.id_comanda
            where pc.id_piesa = p.id_piesa)
    from piesa p
    join furnizor f on f.id_furnizor = p.id_furnizor
    where p.stoc_curent > 0
      and not exists (
            select 1
            from piesa_comanda pc
            join comanda_reparatie c on c.id_comanda = pc.id_comanda
            where pc.id_piesa = p.id_piesa
              and c.data_intrare >= current_date - make_interval(months => p_luni))
    order by 6 desc
$$;


-- =====================================================================
-- 4. VEDERI
-- =====================================================================

-- 4.1 Devizul se calculeaza (CF10)
-- Manopera si piesele sunt agregate separat, ca sa nu se inmulteasca randurile.
create view v_deviz as
select c.id_comanda,
       coalesce(l.manopera, 0)                          as manopera,
       coalesce(p.piese, 0)                             as piese,
       coalesce(l.manopera, 0) + coalesce(p.piese, 0)   as total
from comanda_reparatie c
left join (
    select id_comanda, round(sum(ore_lucrate * tarif_orar_aplicat), 2) as manopera
    from lucrare_efectuata group by id_comanda
) l on l.id_comanda = c.id_comanda
left join (
    select id_comanda, round(sum(cantitate * pret_unitar_aplicat), 2) as piese
    from piesa_comanda group by id_comanda
) p on p.id_comanda = c.id_comanda;


-- 4.2 Comanda cu vehiculul, clientul si operatorul
create view v_comanda_detaliu as
select c.id_comanda,
       c.data_intrare,
       c.data_predare,
       c.km_intrare,
       c.status,
       c.reclamatie,
       c.id_vehicul,
       v.nr_inmatriculare,
       v.marca || ' ' || v.model        as marca_model,
       cl.id_client,
       cl.nume || ' ' || cl.prenume     as client_nume,
       cl.telefon                       as client_telefon,
       c.id_operator,
       a.nume                           as operator_nume
from comanda_reparatie c
join vehicul v  on v.id_vehicul = c.id_vehicul
join client cl  on cl.id_client = v.id_client
join angajat a  on a.id_angajat = c.id_operator;


-- 4.3 Piese sub pragul minim (CF8)
create view v_piese_sub_prag as
select p.id_piesa,
       p.cod,
       p.denumire,
       p.categorie,
       p.stoc_curent,
       p.prag_minim,
       p.prag_minim - p.stoc_curent as deficit,
       f.id_furnizor,
       f.denumire                   as furnizor,
       f.telefon                    as furnizor_telefon
from piesa p
join furnizor f on f.id_furnizor = p.id_furnizor
where p.stoc_curent <= p.prag_minim;


--  4.4 Ultima inspectie ITP pe vehicul + starea valabilitatii (CF14)
create view v_itp_ultima as
select v.id_vehicul,
       v.nr_inmatriculare,
       v.marca || ' ' || v.model        as marca_model,
       cl.id_client,
       cl.nume || ' ' || cl.prenume     as client_nume,
       cl.telefon                       as client_telefon,
       i.data_inspectie,
       i.rezultat,
       i.data_expirare,
       (i.data_expirare - current_date) as zile_ramase,
       case
           when i.id_inspectie is null            then 'NEINSPECTAT'
           when i.rezultat = 'RESPINS'            then 'RESPINS'
           when i.data_expirare < current_date    then 'EXPIRATA'
           when i.data_expirare <= current_date + 30 then 'EXPIRA_CURAND'
           else 'VALABILA'
       end                              as stare
from vehicul v
join client cl on cl.id_client = v.id_client
left join lateral (
    select x.*
    from inspectie_itp x
    where x.id_vehicul = v.id_vehicul
    order by x.data_inspectie desc, x.id_inspectie desc
    limit 1
) i on true;


-- 4.5 Istoricul complet al unui vehicul (comenzi + ITP + programari)
create view v_istoric_vehicul as
select c.id_vehicul,
       c.data_intrare::timestamp                                   as data_eveniment,
       'COMANDA'::text                                             as tip,
       c.id_comanda                                                as id_referinta,
       ('Comanda ' || c.status || ' la ' || c.km_intrare || ' km'
            || coalesce(': ' || c.reclamatie, ''))::text           as descriere
from comanda_reparatie c
union all
select i.id_vehicul,
       i.data_inspectie::timestamp,
       'ITP'::text,
       i.id_inspectie,
       ('ITP ' || i.rezultat || ' la ' || i.km || ' km'
            || coalesce(', expira ' || i.data_expirare::text, ''))::text
from inspectie_itp i
union all
select p.id_vehicul,
       p.data_programare,
       'PROGRAMARE'::text,
       p.id_programare,
       ('Programare ' || p.status
            || coalesce(': ' || p.descriere_problema, ''))::text
from programare p;


--  4.6 Datele de intrare pentru modelul de diagnoza (CF15)
--  Un rand = o categorie de piese inlocuita la o comanda.
create view v_date_ai as
select c.id_comanda,
       v.id_vehicul,
       v.marca,
       v.model,
       v.combustibil,
       v.motorizare,
       (extract(year from c.data_intrare)::integer - v.an_fabricatie) as vechime_ani,
       c.km_intrare,
       p.categorie,
       sum(pc.cantitate)                                              as nr_piese
from comanda_reparatie c
join vehicul v        on v.id_vehicul = c.id_vehicul
join piesa_comanda pc on pc.id_comanda = c.id_comanda
join piesa p          on p.id_piesa = pc.id_piesa
group by c.id_comanda, v.id_vehicul, v.marca, v.model, v.combustibil, v.motorizare,
         c.data_intrare, v.an_fabricatie, c.km_intrare, p.categorie;