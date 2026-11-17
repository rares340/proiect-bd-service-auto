begin;

do $$
declare
    v_an        integer := extract(year from current_date)::integer;
    v_manz      timestamp := (current_date + 30) + time '10:00';
    v_furn integer; v_piesa integer; v_mec integer; v_op integer; v_insp integer;
    v_cl integer; v_veh integer; v_veh_vechi integer; v_cat integer;
    v_com integer; v_com2 integer; v_prog integer; v_i integer;
    v_r record;
    v_num numeric;
    v_d date;
    v_d2 date;
begin
    ------------------------------------------------------------------
    -- Date de baza
    ------------------------------------------------------------------
    insert into furnizor(denumire, cui) values ('Furnizor Test', 'RO999001')
        returning id_furnizor into v_furn;
    insert into piesa(cod, denumire, categorie, pret_vanzare, stoc_curent, prag_minim, id_furnizor)
        values ('T-001', 'Filtru ulei test', 'FILTRE', 100, 10, 3, v_furn)
        returning id_piesa into v_piesa;
    insert into angajat(nume, functie, tarif_orar) values ('Mecanic Test', 'MECANIC', 50)
        returning id_angajat into v_mec;
    insert into angajat(nume, functie) values ('Operator Test', 'OPERATOR')
        returning id_angajat into v_op;
    insert into angajat(nume, functie) values ('Inspector Test', 'INSPECTOR')
        returning id_angajat into v_insp;
    insert into client(nume, prenume, telefon) values ('Test', 'Client', '0700000000')
        returning id_client into v_cl;
    insert into vehicul(serie_sasiu, nr_inmatriculare, marca, model, combustibil, an_fabricatie, id_client)
        values ('TESTVIN0000000001', 'MM01TST', 'Dacia', 'Logan', 'BENZINA', v_an - 5, v_cl)
        returning id_vehicul into v_veh;
    insert into vehicul(serie_sasiu, nr_inmatriculare, marca, model, combustibil, an_fabricatie, id_client)
        values ('TESTVIN0000000002', 'MM02TST', 'Opel', 'Astra', 'MOTORINA', v_an - 20, v_cl)
        returning id_vehicul into v_veh_vechi;
    insert into lucrare_catalog(denumire, durata_ore) values ('Schimb ulei test', 1.5)
        returning id_lucrare_catalog into v_cat;

    insert into comanda_reparatie(km_intrare, reclamatie, id_vehicul, id_operator)
        values (100000, 'zgomot motor', v_veh, v_op)
        returning id_comanda into v_com;

    ------------------------------------------------------------------
    -- STOC (CF7, CF8)
    ------------------------------------------------------------------
    select * into v_r from fn_adauga_piesa_comanda(v_com, v_piesa, 4);
    raise notice '% stoc dupa 4 buc = % (asteptat 6)',
        case when v_r.stoc_ramas = 6 then 'OK  ' else 'ESEC' end, v_r.stoc_ramas;

    select * into v_r from fn_adauga_piesa_comanda(v_com, v_piesa, 4);
    raise notice '% stoc dupa inca 4 buc = %, sub prag = % (asteptat 2, true)',
        case when v_r.stoc_ramas = 2 and v_r.sub_prag then 'OK  ' else 'ESEC' end,
        v_r.stoc_ramas, v_r.sub_prag;

    begin
        perform fn_adauga_piesa_comanda(v_com, v_piesa, 5);
        raise notice 'ESEC  : cantitate peste stoc a fost acceptata';
    exception when others then
        raise notice 'OK    : stoc insuficient refuzat -> %', sqlerrm;
    end;

    select cantitate into v_i from piesa_comanda where id_comanda = v_com and id_piesa = v_piesa;
    raise notice '% cantitate pe comanda = % (asteptat 8, ON CONFLICT a cumulat)',
        case when v_i = 8 then 'OK  ' else 'ESEC' end, v_i;

    select count(*) into v_i from v_piese_sub_prag where id_piesa = v_piesa;
    raise notice '% piesa apare in v_piese_sub_prag', case when v_i = 1 then 'OK  ' else 'ESEC' end;

    ------------------------------------------------------------------
    -- PRET INGHETAT (CNF3)
    ------------------------------------------------------------------
    update piesa set pret_vanzare = 999 where id_piesa = v_piesa;
    select pret_unitar_aplicat into v_num from piesa_comanda
        where id_comanda = v_com and id_piesa = v_piesa;
    raise notice '% pretul pe comanda ramane % dupa scumpire (asteptat 100)',
        case when v_num = 100 then 'OK  ' else 'ESEC' end, v_num;

    begin
        update piesa_comanda set pret_unitar_aplicat = 1 where id_comanda = v_com;
        raise notice 'ESEC  : modificarea pretului aplicat a fost acceptata';
    exception when others then
        raise notice 'OK    : modificare pret aplicat refuzata -> %', sqlerrm;
    end;

    ------------------------------------------------------------------
    -- MANOPERA SI TARIF (CF6, CNF3, CNF4)
    ------------------------------------------------------------------
    insert into lucrare_efectuata(post_lucru, ore_lucrate, tarif_orar_aplicat, id_comanda, id_mecanic, id_lucrare_catalog)
        values ('Post 1', 2, 1, v_com, v_mec, v_cat);
    select tarif_orar_aplicat into v_num from lucrare_efectuata where id_comanda = v_com;
    raise notice '% tariful a fost luat de la mecanic: % (asteptat 50, nu 1)',
        case when v_num = 50 then 'OK  ' else 'ESEC' end, v_num;

    begin
        insert into lucrare_efectuata(ore_lucrate, tarif_orar_aplicat, id_comanda, id_mecanic, id_lucrare_catalog)
            values (1, 50, v_com, v_op, v_cat);
        raise notice 'ESEC  : un operator a fost acceptat ca mecanic';
    exception when others then
        raise notice 'OK    : angajat cu functie gresita refuzat -> %', sqlerrm;
    end;

    begin
        insert into comanda_reparatie(km_intrare, id_vehicul, id_operator) values (1, v_veh, v_mec);
        raise notice 'ESEC  : un mecanic a fost acceptat ca operator';
    exception when others then
        raise notice 'OK    : operator cu functie gresita refuzat -> %', sqlerrm;
    end;

    ------------------------------------------------------------------
    -- DEVIZ (CF10)   manopera 2h x 50 = 100 ; piese 8 x 100 = 800
    ------------------------------------------------------------------
    select * into v_r from v_deviz where id_comanda = v_com;
    raise notice '% deviz: manopera %, piese %, total % (asteptat 100 / 800 / 900)',
        case when v_r.manopera = 100 and v_r.piese = 800 and v_r.total = 900 then 'OK  ' else 'ESEC' end,
        v_r.manopera, v_r.piese, v_r.total;

    ------------------------------------------------------------------
    -- STATUS COMANDA (CF5)
    ------------------------------------------------------------------
    begin
        update comanda_reparatie set status = 'PREDATA' where id_comanda = v_com;
        raise notice 'ESEC  : tranzitia DESCHISA -> PREDATA a fost acceptata';
    exception when others then
        raise notice 'OK    : tranzitie invalida refuzata -> %', sqlerrm;
    end;

    update comanda_reparatie set status = 'IN_LUCRU' where id_comanda = v_com;
    update comanda_reparatie set status = 'FINALIZATA' where id_comanda = v_com;
    raise notice 'OK    : DESCHISA -> IN_LUCRU -> FINALIZATA acceptata';

    begin
        perform fn_adauga_piesa_comanda(v_com, v_piesa, 1);
        raise notice 'ESEC  : piesa adaugata pe comanda finalizata';
    exception when others then
        raise notice 'OK    : comanda finalizata nu mai primeste piese -> %', sqlerrm;
    end;

    update comanda_reparatie set status = 'PREDATA' where id_comanda = v_com;
    select data_predare into v_d from comanda_reparatie where id_comanda = v_com;
    raise notice '% data_predare completata automat: %',
        case when v_d = current_date then 'OK  ' else 'ESEC' end, v_d;

    insert into comanda_reparatie(km_intrare, id_vehicul, id_operator)
        values (100500, v_veh, v_op) returning id_comanda into v_com2;
    update comanda_reparatie set status = 'IN_LUCRU' where id_comanda = v_com2;
    begin
        update comanda_reparatie set status = 'FINALIZATA' where id_comanda = v_com2;
        raise notice 'ESEC  : comanda fara lucrari a fost finalizata';
    exception when others then
        raise notice 'OK    : finalizare fara lucrari refuzata -> %', sqlerrm;
    end;

    ------------------------------------------------------------------
    -- PROGRAMARI (CF4, CF5)
    ------------------------------------------------------------------
    begin
        insert into programare(data_programare, durata_estimata_ore, id_vehicul, id_lucrare_catalog)
            values (localtimestamp - interval '1 day', 1, v_veh, v_cat);
        raise notice 'ESEC  : programare in trecut acceptata';
    exception when others then
        raise notice 'OK    : programare in trecut refuzata -> %', sqlerrm;
    end;

    for v_i in 1..fn_nr_elevatoare() loop
        insert into programare(data_programare, durata_estimata_ore, id_vehicul, id_lucrare_catalog)
            values (v_manz, 2, v_veh, v_cat);
    end loop;
    raise notice 'OK    : % programari simultane acceptate (= nr. elevatoare)', fn_nr_elevatoare();

    begin
        insert into programare(data_programare, durata_estimata_ore, id_vehicul, id_lucrare_catalog)
            values (v_manz + interval '1 hour', 2, v_veh, v_cat);
        raise notice 'ESEC  : programare peste numarul de elevatoare acceptata';
    exception when others then
        raise notice 'OK    : fara elevator liber -> %', sqlerrm;
    end;

    insert into programare(data_programare, durata_estimata_ore, id_vehicul, id_lucrare_catalog, descriere_problema)
        values (v_manz + interval '1 day', 1, v_veh, v_cat, 'franare slaba')
        returning id_programare into v_prog;
    call sp_deschide_comanda_din_programare(v_prog, 101000, v_op, v_i);
    select status, id_comanda into v_r from programare where id_programare = v_prog;
    raise notice '% programare -> comanda %: status %, id_comanda % (asteptat ONORATA)',
        case when v_r.status = 'ONORATA' and v_r.id_comanda = v_i then 'OK  ' else 'ESEC' end,
        v_i, v_r.status, v_r.id_comanda;

    ------------------------------------------------------------------
    -- ITP (CF12, CF13, CF14)
    ------------------------------------------------------------------
    -- prima inspectie a unui vehicul de 5 ani, facuta acum 3 ani -> 3 ani valabilitate
    insert into inspectie_itp(data_inspectie, km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
        values ((current_date - interval '3 years')::date, 60000, 1.0, 70, 'ADMIS', v_veh, v_insp)
        returning data_inspectie, data_expirare into v_d, v_d2;
    raise notice '% prima ITP: expirare % (asteptat %, +3 ani)',
        case when v_d2 = (v_d + interval '3 years')::date then 'OK  ' else 'ESEC' end,
        v_d2, (v_d + interval '3 years')::date;

    -- a doua inspectie, acum -> 2 ani
    insert into inspectie_itp(data_inspectie, km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
        values (current_date, 100000, 1.0, 70, 'ADMIS', v_veh, v_insp)
        returning data_inspectie, data_expirare into v_d, v_d2;
    raise notice '% a doua ITP: expirare % (asteptat %, +2 ani)',
        case when v_d2 = (v_d + interval '2 years')::date then 'OK  ' else 'ESEC' end,
        v_d2, (v_d + interval '2 years')::date;

    -- vehicul de 20 de ani -> 1 an
    insert into inspectie_itp(km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
        values (250000, 1.0, 70, 'ADMIS', v_veh_vechi, v_insp)
        returning data_inspectie, data_expirare into v_d, v_d2;
    raise notice '% vehicul vechi: expirare % (asteptat %, +1 an)',
        case when v_d2 = (v_d + interval '1 year')::date then 'OK  ' else 'ESEC' end,
        v_d2, (v_d + interval '1 year')::date;

    begin
        insert into inspectie_itp(km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
            values (100000, 1.0, 30, 'ADMIS', v_veh, v_insp);
        raise notice 'ESEC  : ADMIS cu franare slaba acceptat';
    exception when others then
        raise notice 'OK    : ADMIS cu franare slaba refuzat -> %', sqlerrm;
    end;

    begin
        insert into inspectie_itp(km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
            values (100000, 5.0, 70, 'ADMIS', v_veh, v_insp);
        raise notice 'ESEC  : ADMIS cu CO peste limita acceptat';
    exception when others then
        raise notice 'OK    : ADMIS cu CO peste limita refuzat -> %', sqlerrm;
    end;

    insert into inspectie_itp(km, emisii_co, eficienta_franare, rezultat, data_expirare, id_vehicul, id_inspector)
        values (100000, 5.0, 30, 'RESPINS', current_date + 100, v_veh, v_insp)
        returning data_expirare into v_d;
    raise notice '% RESPINS nu pastreaza data expirarii: %',
        case when v_d is null then 'OK  ' else 'ESEC' end, v_d;

    begin
        insert into inspectie_itp(km, emisii_co, eficienta_franare, rezultat, id_vehicul, id_inspector)
            values (100000, 1.0, 70, 'ADMIS', v_veh, v_mec);
        raise notice 'ESEC  : un mecanic a fost acceptat ca inspector';
    exception when others then
        raise notice 'OK    : inspector cu functie gresita refuzat -> %', sqlerrm;
    end;

    select stare into v_r from v_itp_ultima where id_vehicul = v_veh_vechi;
    raise notice 'INFO  : stare ITP vehicul vechi in v_itp_ultima = %', v_r.stare;

    ------------------------------------------------------------------
    -- UTILIZATORI (CF2, CNF4)
    ------------------------------------------------------------------
    begin
        insert into utilizator(nume_utilizator, parola, rol) values ('t_op', 'x', 'OPERATOR');
        raise notice 'ESEC  : operator fara angajat acceptat';
    exception when others then
        raise notice 'OK    : operator fara angajat refuzat -> %', sqlerrm;
    end;

    insert into utilizator(nume_utilizator, parola, rol) values ('t_admin', 'x', 'ADMINISTRATOR');
    begin
        delete from utilizator where nume_utilizator = 't_admin';
        raise notice 'ESEC  : utilizator sters';
    exception when others then
        raise notice 'OK    : stergere utilizator refuzata -> %', sqlerrm;
    end;

    ------------------------------------------------------------------
    -- VEDERI SI RAPOARTE (verificare ca ruleaza)
    ------------------------------------------------------------------
    select count(*) into v_i from v_istoric_vehicul where id_vehicul = v_veh;
    raise notice 'INFO  : v_istoric_vehicul are % evenimente pentru vehiculul de test', v_i;

    select count(*) into v_i from v_date_ai where id_vehicul = v_veh;
    raise notice 'INFO  : v_date_ai are % randuri pentru vehiculul de test', v_i;

    select count(*) into v_i from fn_raport_productivitate(current_date - 1, current_date + 1);
    raise notice 'INFO  : fn_raport_productivitate a returnat % randuri', v_i;

    select count(*) into v_i from fn_raport_profitabilitate(current_date - 1, current_date + 1);
    raise notice 'INFO  : fn_raport_profitabilitate a returnat % randuri', v_i;

    select count(*) into v_i from fn_piese_fara_rulaj(12);
    raise notice 'INFO  : fn_piese_fara_rulaj a returnat % randuri', v_i;

    select count(*) into v_i from v_comanda_detaliu where id_comanda = v_com;
    raise notice '% v_comanda_detaliu returneaza comanda de test', case when v_i = 1 then 'OK  ' else 'ESEC' end;

    raise notice '--- Gata. Totul se anuleaza prin ROLLBACK. ---';
end $$;

rollback;