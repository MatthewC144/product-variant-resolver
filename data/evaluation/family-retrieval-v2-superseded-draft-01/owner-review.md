# Final v2 — 105 題待確認清單

狀態：等待專案 owner 確認；尚無正式答案、候選或評分。

整份 query-pack SHA-256：`e52902e72e057d125e984eae81bfe78bf1859a8d7fed366f2277f734510c4d14`

選定模型提交：`a9a3730bf4d6ae47ddb1fff853e951081c81570c`；設定：0.50 / 1.0。

請確認題目與『打算驗證的對象』是否合理；這些對象只是審核參考，不是模型輸出。
正例：應找回對應 casting family；合併：應沿用既有人工 casting，不另建 family。
暫緩：該 family 尚未核准建立，不要求所有人工候選為空。無關：應沒有人工知識候選。

84 正例（42 車款各兩種題型）、4 合併、7 暫緩、10 無關。
題目是人工／AI 編寫的合成題，不是新抓取的市場資料；同一批車款，不是未見車款測試。
作者知道舊開發結果，但未執行或查看這 105 題的新候選。人工確認不能消除所有來源偏差。

每題完整校驗碼在 query-pack-manifest.json 的 case_sha256；下表顯示前 12 位供對照。

| # | Case ID | 類型 | 打算驗證的對象 | Query（完整原文） | Case SHA 前12位 |
|---:|---|---|---|---|---|
| 1 | fr2-hold-089ff8645b5f2de7 | 暫緩 / held_identity | '55 Chevy | Chevrolet fifty-five casting; seller unsure which original tool this is | `ec2d0d7835e5` |
| 2 | fr2-hold-0e07a7139454d2e8 | 暫緩 / held_identity | Nissan Skyline GT-R (BNR32) | Nissan Skyline GT-R R32 labelled BNR32; base stamp not photographed | `d2bab49dbc23` |
| 3 | fr2-hold-369b0be5855c0a1c | 暫緩 / held_identity | Nissan Skyline 2000GT-R LBWK | Liberty Walk Nissan Skyline 2000 GT-R without a readable base stamp | `8a793f37b3b6` |
| 4 | fr2-hold-4f9ee66afdfe8cac | 暫緩 / held_identity | Power Wheels Dune Racer | Power Wheels Dune Racer miniature beside a handwritten garage-sale tag | `72f68db35698` |
| 5 | fr2-hold-8403e21a29c27eab | 暫緩 / held_identity | Standard Kart | Standard Kart with Mario markings; chassis version absent from listing | `1b6944a5b1e1` |
| 6 | fr2-hold-8d24c626a51b1804 | 暫緩 / held_identity | Batman and Robin Batmobile | Batman and Robin Batmobile; seller gives no movie/tool lineage information | `db0c49c1d432` |
| 7 | fr2-hold-c639dc688e21d33b | 暫緩 / held_identity | Mazda MX-5 Miata | MX-5 Mazda Miata offered without generation or tooling description | `10cd55d78186` |
| 8 | fr2-merge-04829924a36830a6 | 合併 / merge_existing_family | Purple Passion | Purple Passion blue hot rod photographed beside an empty display plinth | `b1777920d729` |
| 9 | fr2-merge-6062af64f2e5a66c | 合併 / merge_existing_family | Tesla Model S Plaid | Tesla Model S Plaid red saloon with sticker residue on the windshield | `300590da66f4` |
| 10 | fr2-merge-aa499ddb791c6991 | 合併 / merge_existing_family | '67 Chevy C10 | Chevy C10 from 1967 with orange paint and a creased hanger tab | `190391f518f3` |
| 11 | fr2-merge-b60363832032d566 | 合併 / merge_existing_family | Subaru BRZ | Subaru BRZ blue coupe found in garage cartons with scratched blister | `08724ac0ce0a` |
| 12 | fr2-positive-0573861db69878eb-lexical_variation | 正例 / lexical_variation | Max Steel | maxstiel fantasy racer wanted | `bed257c5899f` |
| 13 | fr2-positive-0573861db69878eb-marketplace_noise | 正例 / marketplace_noise | Max Steel | Rear blister dent on blue Max Steel from weekend swap table | `1edc394da2d8` |
| 14 | fr2-positive-08cb7fadb9fed12d-lexical_variation | 正例 / lexical_variation | 1988 Jeep Wagoneer | jeep wagonear eighty eight casting | `df17d5245bcc` |
| 15 | fr2-positive-08cb7fadb9fed12d-marketplace_noise | 正例 / marketplace_noise | 1988 Jeep Wagoneer | Seller found 1988 Jeep Wagoneer under an old display stand | `872d57a8e189` |
| 16 | fr2-positive-1555c05ceeb491cb-lexical_variation | 正例 / lexical_variation | '94 Audi Avant RS2 | audi rs-two avante 1994 estate | `9729ce160d08` |
| 17 | fr2-positive-1555c05ceeb491cb-marketplace_noise | 正例 / marketplace_noise | '94 Audi Avant RS2 | Silver 94 Audi Avant RS2 with price sticker across front window | `5b9265afcdab` |
| 18 | fr2-positive-174efb9bce3a441e-lexical_variation | 正例 / lexical_variation | Lamborghini Huracán Sterrato | lmborghini huracn sterratto offroader | `e93b176b68ff` |
| 19 | fr2-positive-174efb9bce3a441e-marketplace_noise | 正例 / marketplace_noise | Lamborghini Huracán Sterrato | Dusty orange Lamborghini Huracan Sterrato photographed beside its blister | `1be445a0bfb2` |
| 20 | fr2-positive-18e55e067083dbd1-lexical_variation | 正例 / lexical_variation | '87 Audi quattro | audy quatrro eighty-seven rally miniature | `d1c66e1f52dd` |
| 21 | fr2-positive-18e55e067083dbd1-marketplace_noise | 正例 / marketplace_noise | '87 Audi quattro | 87 Audi quattro has a bent hanger tab and silver paint flecks | `0f90237ee084` |
| 22 | fr2-positive-1b2a4227b4e5decd-lexical_variation | 正例 / lexical_variation | Mercedes-Benz 500 E | mercedez five-hundred-E saloon | `5ebcaab2160c` |
| 23 | fr2-positive-1b2a4227b4e5decd-marketplace_noise | 正例 / marketplace_noise | Mercedes-Benz 500 E | Seller bundles black Mercedes Benz 500 E with an empty acrylic stand | `bb2a0f3dbb2f` |
| 24 | fr2-positive-2357e7eb6b4e62b8-lexical_variation | 正例 / lexical_variation | Monster High Ghoul Mobile | ghoul mobil from monster high | `c605182702af` |
| 25 | fr2-positive-2357e7eb6b4e62b8-marketplace_noise | 正例 / marketplace_noise | Monster High Ghoul Mobile | Pink Monster High Ghoul Mobile shown outside packaging on a cloth | `33b63f7a14a6` |
| 26 | fr2-positive-356e4ef63275a661-lexical_variation | 正例 / lexical_variation | Fish'd & Chip'd | fishd and chipd novelty casting | `b1ea2ddc7159` |
| 27 | fr2-positive-356e4ef63275a661-marketplace_noise | 正例 / marketplace_noise | Fish'd & Chip'd | Green Fish'd & Chip'd with shelf dust and a crumpled price tag | `6f82c4528847` |
| 28 | fr2-positive-39b248ce2f3723cd-lexical_variation | 正例 / lexical_variation | Twin Mill Gen-E | twinmil gen-ee electric concept | `43d8882ecc6b` |
| 29 | fr2-positive-39b248ce2f3723cd-marketplace_noise | 正例 / marketplace_noise | Twin Mill Gen-E | Twin Mill Gen-E silver paint photographed on the seller's desk | `eba4aff72411` |
| 30 | fr2-positive-3c9f928f085efaae-lexical_variation | 正例 / lexical_variation | Kick Kart | kickkart kart racer miniature | `78af5f01370f` |
| 31 | fr2-positive-3c9f928f085efaae-marketplace_noise | 正例 / marketplace_noise | Kick Kart | Kick Kart yellow fantasy racer with shop stamp on cardboard back | `f4e9ab6ffdb6` |
| 32 | fr2-positive-440103f8ef3c6b70-lexical_variation | 正例 / lexical_variation | Haulerback | hawlerback hauler casting | `0f58753bc417` |
| 33 | fr2-positive-440103f8ef3c6b70-marketplace_noise | 正例 / marketplace_noise | Haulerback | Haulerback purple truck pulled from a dusty cabinet after moving house | `bb839fc180e5` |
| 34 | fr2-positive-45af5b93f3f6650f-lexical_variation | 正例 / lexical_variation | Custom Cadillac Fleetwood | cust Cadillac Fleetwod lowrider | `ebd866893c12` |
| 35 | fr2-positive-45af5b93f3f6650f-marketplace_noise | 正例 / marketplace_noise | Custom Cadillac Fleetwood | Gold Custom Cadillac Fleetwood has rubbed corners on its backing card | `a98b06efb73b` |
| 36 | fr2-positive-4bf5341a133d433b-lexical_variation | 正例 / lexical_variation | Hirohata Merc | hirohata merck custom coupe | `bb2242d58664` |
| 37 | fr2-positive-4bf5341a133d433b-marketplace_noise | 正例 / marketplace_noise | Hirohata Merc | Teal Hirohata Merc with scratched blister offered at a toy swap | `06b0cbbe0d99` |
| 38 | fr2-positive-4d00e96d12341b4d-lexical_variation | 正例 / lexical_variation | Nerve Hammer | nervehamer fantasy hammer car | `bd22e93b8ba1` |
| 39 | fr2-positive-4d00e96d12341b4d-marketplace_noise | 正例 / marketplace_noise | Nerve Hammer | Orange Nerve Hammer pictured with a torn receipt beneath the stand | `43a7daabb625` |
| 40 | fr2-positive-4d2de6db3d5bba63-lexical_variation | 正例 / lexical_variation | Crescendo | crecsendo music inspired casting | `8770baf365fc` |
| 41 | fr2-positive-4d2de6db3d5bba63-marketplace_noise | 正例 / marketplace_noise | Crescendo | Red Crescendo music car in a cloudy blister with faded shop sticker | `88492230d5fc` |
| 42 | fr2-positive-526b697937fde7cc-lexical_variation | 正例 / lexical_variation | '80 El Camino | 1980 el camno pickup casting | `8958eb7fa41b` |
| 43 | fr2-positive-526b697937fde7cc-marketplace_noise | 正例 / marketplace_noise | '80 El Camino | 80 El Camino black pickup from garage collection; hanger tab creased | `39d0a4e08f03` |
| 44 | fr2-positive-57cf5c31afbadc57-lexical_variation | 正例 / lexical_variation | The Vanster | the vansterr fantasy van | `9df6e1701e23` |
| 45 | fr2-positive-57cf5c31afbadc57-marketplace_noise | 正例 / marketplace_noise | The Vanster | Green The Vanster with loose axle photographed at a flea-market stall | `91428c79aeb8` |
| 46 | fr2-positive-59e5682e50af879e-lexical_variation | 正例 / lexical_variation | Proton Saga | proton sagga malaysian saloon | `84c9b2c14c3a` |
| 47 | fr2-positive-59e5682e50af879e-marketplace_noise | 正例 / marketplace_noise | Proton Saga | White Proton Saga from storage tub; paint has a tiny roof chip | `8ee74bf80bb6` |
| 48 | fr2-positive-7e221ec8ecd02815-lexical_variation | 正例 / lexical_variation | X-34 Landspeeder | x thirty-four landspeeder vehicle | `60e97805159c` |
| 49 | fr2-positive-7e221ec8ecd02815-marketplace_noise | 正例 / marketplace_noise | X-34 Landspeeder | Tan X-34 Landspeeder Star Wars toy beside a handwritten price label | `cdb16bc3e435` |
| 50 | fr2-positive-85226ac5ac0d3f77-lexical_variation | 正例 / lexical_variation | Fiat 500e | fiat 500 ee electric hatchback | `3b6f4f434245` |
| 51 | fr2-positive-85226ac5ac0d3f77-marketplace_noise | 正例 / marketplace_noise | Fiat 500e | Yellow Fiat 500e has crushed packaging near the lower right corner | `5a77eba2129e` |
| 52 | fr2-positive-85e407525ac7bf41-lexical_variation | 正例 / lexical_variation | Small Bloc | smal bloc fantasy smallblock | `29e4781e1a2e` |
| 53 | fr2-positive-85e407525ac7bf41-marketplace_noise | 正例 / marketplace_noise | Small Bloc | Blue Small Bloc with rubbed roof; seller cannot locate original blister | `57041bc13750` |
| 54 | fr2-positive-89930c384be2e8bf-lexical_variation | 正例 / lexical_variation | Kowloon'd Hypervan | kowloond hyper-van custom van | `116f0334c4b5` |
| 55 | fr2-positive-89930c384be2e8bf-marketplace_noise | 正例 / marketplace_noise | Kowloon'd Hypervan | Red Kowloon'd Hypervan from display cabinet; price sticker left on back | `a5c1d5c3a412` |
| 56 | fr2-positive-8a07157f2af2ddd5-lexical_variation | 正例 / lexical_variation | Bogzilla | bogzillla monster racer miniature | `de79b3fe43d6` |
| 57 | fr2-positive-8a07157f2af2ddd5-marketplace_noise | 正例 / marketplace_noise | Bogzilla | Bogzilla green creature racer shown next to a cracked protective case | `7c2a30c0331a` |
| 58 | fr2-positive-8cce01fa7d44112a-lexical_variation | 正例 / lexical_variation | Deora III | deorra iii surf concept | `eae3007148fe` |
| 59 | fr2-positive-8cce01fa7d44112a-marketplace_noise | 正例 / marketplace_noise | Deora III | Purple Deora III with a shop security label covering the collector art | `f8faa9cad40f` |
| 60 | fr2-positive-9069156ec909a92e-lexical_variation | 正例 / lexical_variation | Donut Drifter | doughnut drifter pastry car | `548ea98040d0` |
| 61 | fr2-positive-9069156ec909a92e-marketplace_noise | 正例 / marketplace_noise | Donut Drifter | Pink Donut Drifter with bent card edges photographed on a kitchen cloth | `d192fffd0bb0` |
| 62 | fr2-positive-99200212d1475ef2-lexical_variation | 正例 / lexical_variation | 2020 Ram 1500 Rebel | 2020 ram 15 hundred rebel truck | `0786b4609b0c` |
| 63 | fr2-positive-99200212d1475ef2-marketplace_noise | 正例 / marketplace_noise | 2020 Ram 1500 Rebel | 2020 Ram 1500 Rebel pickup from seller's cabinet; dusty but boxed | `9d21f54fa706` |
| 64 | fr2-positive-a1b198f7d235f778-lexical_variation | 正例 / lexical_variation | Ford Performance SuperVan 4 | ford performance supervn iv racer | `1c16bb00caaf` |
| 65 | fr2-positive-a1b198f7d235f778-marketplace_noise | 正例 / marketplace_noise | Ford Performance SuperVan 4 | White Ford Performance SuperVan 4 offered with a damaged acrylic stand | `0fbd4665a434` |
| 66 | fr2-positive-a2097eead3bd8db9-lexical_variation | 正例 / lexical_variation | '66 Buick Riviera | 1966 buick riviera coupe miniature | `9828872f6856` |
| 67 | fr2-positive-a2097eead3bd8db9-marketplace_noise | 正例 / marketplace_noise | '66 Buick Riviera | 66 Buick Riviera teal paint under cloudy blister; seller notes shelf wear | `31eb90e4744b` |
| 68 | fr2-positive-a8e0dec4abdc4131-lexical_variation | 正例 / lexical_variation | DMC DeLorean | dmc de-lorien stainless coupe | `03ff3ed9d500` |
| 69 | fr2-positive-a8e0dec4abdc4131-marketplace_noise | 正例 / marketplace_noise | DMC DeLorean | Silver DMC DeLorean found in moving cartons with no paper receipt | `17b9a9e278ed` |
| 70 | fr2-positive-aaafff57ac4d4daa-lexical_variation | 正例 / lexical_variation | Morgan Super 3 | morgan supr 3 three-wheeler | `823ab294d0f1` |
| 71 | fr2-positive-aaafff57ac4d4daa-marketplace_noise | 正例 / marketplace_noise | Morgan Super 3 | Red Morgan Super 3 sits on an unmarked stand; rear blister is split | `b5c2a875a3d8` |
| 72 | fr2-positive-aab5350cb90d72ed-lexical_variation | 正例 / lexical_variation | '21 Ford Bronco | ford brnoco twenty-one SUV | `d8b7f68e9ab7` |
| 73 | fr2-positive-aab5350cb90d72ed-marketplace_noise | 正例 / marketplace_noise | '21 Ford Bronco | 21 Ford Bronco blue off-road toy photographed with wrinkled price label | `a4dcce6d2dde` |
| 74 | fr2-positive-aec11693bfe04245-lexical_variation | 正例 / lexical_variation | Mazda REPU | mazda rep-u rotary pickup casting | `79325bc5bf10` |
| 75 | fr2-positive-aec11693bfe04245-marketplace_noise | 正例 / marketplace_noise | Mazda REPU | Mazda REPU orange rotary pickup displayed beside its torn backing card | `dd70732c1dce` |
| 76 | fr2-positive-b31d285560d8a242-lexical_variation | 正例 / lexical_variation | Ford Mustang GTD | mustangg gtd ford track coupe | `e41da889d8fb` |
| 77 | fr2-positive-b31d285560d8a242-marketplace_noise | 正例 / marketplace_noise | Ford Mustang GTD | Grey Ford Mustang GTD from a toy swap; scratched clear plastic cover | `8ebe65032fa6` |
| 78 | fr2-positive-b3cd4f5a5f7e196a-lexical_variation | 正例 / lexical_variation | '69 Corvette Racer | 1969 corvette racr competition car | `fa2a045e1fe9` |
| 79 | fr2-positive-b3cd4f5a5f7e196a-marketplace_noise | 正例 / marketplace_noise | '69 Corvette Racer | 69 Corvette Racer yellow paint with old shop sticker still attached | `deb14a55f237` |
| 80 | fr2-positive-c655fb5244c584ae-lexical_variation | 正例 / lexical_variation | Kei Swap | kei swapp modified microtruck | `c54f4610a0af` |
| 81 | fr2-positive-c655fb5244c584ae-marketplace_noise | 正例 / marketplace_noise | Kei Swap | Red Kei Swap parked on seller's desk; backing card folded at top | `f7294810a613` |
| 82 | fr2-positive-d114c33db6fa215b-lexical_variation | 正例 / lexical_variation | '90 Honda Civic EF | honda civik e-f from ninety | `e9b959588fec` |
| 83 | fr2-positive-d114c33db6fa215b-marketplace_noise | 正例 / marketplace_noise | '90 Honda Civic EF | 90 Honda Civic EF white hatchback pictured beside a crumpled shop bag | `0656ca1c1f02` |
| 84 | fr2-positive-d5c83bb87be8cab0-lexical_variation | 正例 / lexical_variation | Super Twin Mill | super twinmill twin engine fantasy | `2f0e5d316b06` |
| 85 | fr2-positive-d5c83bb87be8cab0-marketplace_noise | 正例 / marketplace_noise | Super Twin Mill | Chrome Super Twin Mill has dusty packaging and a faded price sticker | `d806748e1fa7` |
| 86 | fr2-positive-d816204cf649a0c0-lexical_variation | 正例 / lexical_variation | Draftnator | draftinator drafting racer miniature | `3221baccec4e` |
| 87 | fr2-positive-d816204cf649a0c0-marketplace_noise | 正例 / marketplace_noise | Draftnator | Black Draftnator with wrinkled backing card and no original sales receipt | `87158023fae8` |
| 88 | fr2-positive-d90841788b1d98a2-lexical_variation | 正例 / lexical_variation | Alpha Pursuit | alpha persuit police casting | `413af9f1ff16` |
| 89 | fr2-positive-d90841788b1d98a2-marketplace_noise | 正例 / marketplace_noise | Alpha Pursuit | Blue Alpha Pursuit patrol car has a scratch along its clear blister | `9edab1d94f85` |
| 90 | fr2-positive-db3fe3a0103099ec-lexical_variation | 正例 / lexical_variation | '22 Ford Maverick Custom | 2022 ford maverik cust pickup | `62f0071f80a2` |
| 91 | fr2-positive-db3fe3a0103099ec-marketplace_noise | 正例 / marketplace_noise | '22 Ford Maverick Custom | 22 Ford Maverick Custom red truck photographed beside a damaged stand | `82c562e5b703` |
| 92 | fr2-positive-e7d4d8cf1dd8c6e1-lexical_variation | 正例 / lexical_variation | Mazda Autozam | mazda autozamm kei coupe | `9e8409211c12` |
| 93 | fr2-positive-e7d4d8cf1dd8c6e1-marketplace_noise | 正例 / marketplace_noise | Mazda Autozam | Blue Mazda Autozam removed from an old cabinet; seller reports roof rub | `f46cf6132f44` |
| 94 | fr2-positive-fd96307f2dc8b421-lexical_variation | 正例 / lexical_variation | Custom '53 Chevy | custom chevie fifty-three pickup | `3b3e932dcf04` |
| 95 | fr2-positive-fd96307f2dc8b421-marketplace_noise | 正例 / marketplace_noise | Custom '53 Chevy | Custom 53 Chevy red pickup found in garage carton with torn price tag | `6a99d447d214` |
| 96 | fr2-unrelated-00 | 無關 / no_overlap | 非車款詞語 | quinoa | `5f0f6156e000` |
| 97 | fr2-unrelated-01 | 無關 / no_overlap | 非車款詞語 | origami | `6f1d4ea2c00a` |
| 98 | fr2-unrelated-02 | 無關 / no_overlap | 非車款詞語 | sourdough | `b69175d28377` |
| 99 | fr2-unrelated-03 | 無關 / no_overlap | 非車款詞語 | percolator | `188d226c371b` |
| 100 | fr2-unrelated-04 | 無關 / no_overlap | 非車款詞語 | ukulele | `50e7e18a710b` |
| 101 | fr2-unrelated-05 | 無關 / no_overlap | 非車款詞語 | tapestry | `1fa377713073` |
| 102 | fr2-unrelated-06 | 無關 / no_overlap | 非車款詞語 | metronome | `211c9820f477` |
| 103 | fr2-unrelated-07 | 無關 / no_overlap | 非車款詞語 | stethoscope | `2fadfa9280e8` |
| 104 | fr2-unrelated-08 | 無關 / no_overlap | 非車款詞語 | embroidery | `562dcdce77de` |
| 105 | fr2-unrelated-09 | 無關 / no_overlap | 非車款詞語 | thermocouple | `f3b81278131d` |

若有題目不合理，請指出 Case ID；尚未評分，可以版本化修訂後重新確認。
若全部合理，請明確確認『同意這 105 題及其對應對象作為 final v2 測試』，並指向本份校驗碼。
只有確認後，才記錄你的審核、建立正式 expected labels／benchmark；benchmark 提交後才跑一次 final。
