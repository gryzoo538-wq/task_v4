<?php
/**
 * Usage: php tests/run_tests.php <output folder>
 * e.g.   php tests/run_tests.php ../../output/phase1
 *
 * Loads the real plugin on top of tests/wp-stubs.php, imports
 * <folder>/woocommerce_import.csv and checks the importer, the product tab and
 * the [coa_library] shortcode against coa_library.html and coa_feed.json.
 */

if ( $argc < 2 ) {
	fwrite( STDERR, "usage: php tests/run_tests.php <output folder>\n" );
	exit( 2 );
}
$dir = rtrim( $argv[1], '/' );
foreach ( array( 'woocommerce_import.csv', 'coa_library.html', 'coa_feed.json' ) as $f ) {
	if ( ! is_file( "$dir/$f" ) ) {
		fwrite( STDERR, "missing $dir/$f\n" );
		exit( 2 );
	}
}

require __DIR__ . '/wp-stubs.php';
require dirname( __DIR__ ) . '/peptide-coa.php';

$pass = 0;
$fail = 0;
function check( $cond, $label, $detail = '' ) {
	global $pass, $fail;
	if ( $cond ) {
		$pass++;
		echo "PASS  $label\n";
	} else {
		$fail++;
		echo "FAIL  $label" . ( '' !== $detail ? "\n      $detail" : '' ) . "\n";
	}
}

echo "Peptide COA plugin tests against $dir\n\n";

// ---------------------------------------------------------------- 1. import
$importer = new Peptide_COA_Importer();
$parsed   = $importer->read_file( "$dir/woocommerce_import.csv" );
$csv      = array_values( $parsed['rows'] );
check( 30 === count( $csv ) && ! $parsed['errors'], 'import file has 30 data rows', count( $csv ) . ' rows' );

$result = $importer->import_file( "$dir/woocommerce_import.csv" );
check( 30 === $result['imported'], 'all 30 rows imported', 'imported ' . $result['imported'] );
check( array() === $result['errors'], 'no validation errors', json_encode( $result['errors'] ) );
check( 30 === count( $GLOBALS['pcoa_posts'] ), '30 WooCommerce products exist after import' );

$meta_ok = true;
$bad     = array();
foreach ( $csv as $row ) {
	$id = wc_get_product_id_by_sku( $row['SKU'] );
	$p  = wc_get_product( $id );
	if ( ! $p || $p->get_status() !== $row['Status'] || $p->get_regular_price() !== $row['Regular price'] || $p->get_name() !== $row['Name'] ) {
		$meta_ok = false;
		$bad[]   = $row['SKU'] . ' product fields';
	}
	foreach ( Peptide_COA_Importer::META as $col => $key ) {
		if ( (string) get_post_meta( $id, $key, true ) !== $row[ $col ] ) {
			$meta_ok = false;
			$bad[]   = $row['SKU'] . " $key";
		}
	}
}
check( $meta_ok, 'every row stored as product + _coa_* meta exactly as in the CSV', implode( ', ', $bad ) );

// re-import is idempotent (updates, does not duplicate)
$again = $importer->import_file( "$dir/woocommerce_import.csv" );
check( 30 === $again['imported'] && 30 === count( $GLOBALS['pcoa_posts'] ), 're-import updates existing products (still 30)' );

// ---------------------------------------------------------------- 2. shortcode vs library / feed
$html = file_get_contents( "$dir/coa_library.html" );
$feed = json_decode( file_get_contents( "$dir/coa_feed.json" ), true );
preg_match_all( '/<tr data-sku="([^"]+)"/', $html, $m );
$lib_skus  = $m[1];
$feed_skus = array_column( $feed['products'], 'sku' );

$sc = do_shortcode( '[coa_library]' );
preg_match_all( '/<tr data-sku="([^"]+)"/', $sc, $m );
$sc_skus = $m[1];

$pub_skus = array();
foreach ( $csv as $row ) {
	if ( 'publish' === $row['Status'] ) {
		$pub_skus[] = $row['SKU'];
	}
}
check( count( $sc_skus ) > 0, 'shortcode renders rows', count( $sc_skus ) . ' rows' );
check( $sc_skus === $lib_skus, 'shortcode lists the same SKUs in the same order as coa_library.html',
	'shortcode: ' . implode( ',', $sc_skus ) . "\n      library:   " . implode( ',', $lib_skus ) );
check( $sc_skus === $feed_skus, 'shortcode order matches coa_feed.json', 'feed: ' . implode( ',', $feed_skus ) );
$sorted_pub = $pub_skus;
sort( $sorted_pub );
$sorted_sc = $sc_skus;
sort( $sorted_sc );
check( $sorted_pub === $sorted_sc, 'shortcode lists exactly the published SKUs of the import file' );

// rows of the shortcode carry the imported values
$rows_ok = true;
foreach ( Peptide_COA_Display::library_rows() as $r ) {
	foreach ( $feed['products'] as $fp ) {
		if ( $fp['sku'] === $r['sku'] && ( $fp['batch'] !== $r['batch'] || $fp['test_date'] !== $r['test_date'] || abs( $fp['purity'] - (float) $r['purity'] ) > 1e-9 || $fp['coa_url'] !== $r['url'] ) ) {
			$rows_ok = false;
		}
	}
}
check( $rows_ok, 'shortcode batch / test date / purity / URL equal the feed values' );

// ---------------------------------------------------------------- 3. teaser
preg_match( '/<p class="coa-teaser"[^>]*>([^<]*)<\/p>/', $sc, $t );
$sc_teaser = html_entity_decode( $t[1] ?? '', ENT_QUOTES, 'UTF-8' );
preg_match( '/id="coa-teaser">([^<]*)</', $html, $t2 );
$html_teaser = html_entity_decode( $t2[1] ?? '', ENT_QUOTES, 'UTF-8' );
$teaser      = Peptide_COA_Display::teaser( Peptide_COA_Display::library_rows() );
check( $sc_teaser === $feed['teaser']['text'], 'shortcode teaser text matches coa_feed.json', "\"$sc_teaser\" vs \"{$feed['teaser']['text']}\"" );
check( $teaser['count'] === $feed['teaser']['verified_coas'], 'teaser count matches feed', $teaser['count'] . ' vs ' . $feed['teaser']['verified_coas'] );
check( abs( $teaser['mean'] - $feed['teaser']['average_purity'] ) < 1e-9, 'teaser mean purity matches feed', $teaser['mean'] . ' vs ' . $feed['teaser']['average_purity'] );
check( $html_teaser === $feed['teaser']['text'], 'coa_library.html teaser matches feed' );
$sum = 0;
foreach ( $csv as $row ) {
	if ( 'publish' === $row['Status'] ) {
		$sum += (float) $row['coa_purity'];
	}
}
$csv_mean = count( $pub_skus ) ? round( $sum / count( $pub_skus ) + 1e-12, 2 ) : 0;
check( count( $pub_skus ) === $teaser['count'] && abs( $csv_mean - $teaser['mean'] ) < 1e-9, 'teaser numbers equal the import file (published count and mean purity)',
	count( $pub_skus ) . " / $csv_mean" );

// ---------------------------------------------------------------- 4. product tab
$tabs = apply_filters( 'woocommerce_product_tabs', array() );
check( isset( $tabs['peptide_coa'] ) && 'Certificate of Analysis' === $tabs['peptide_coa']['title'], 'woocommerce_product_tabs adds a "Certificate of Analysis" tab' );
$draft_ok = true;
$pub_ok   = true;
$drafts   = 0;
$problems = array();
foreach ( $csv as $row ) {
	global $product;
	$product = wc_get_product( wc_get_product_id_by_sku( $row['SKU'] ) );
	ob_start();
	call_user_func( $tabs['peptide_coa']['callback'], 'peptide_coa', $tabs['peptide_coa'] );
	$out = ob_get_clean();
	if ( 'draft' === $row['Status'] ) {
		$drafts++;
		$leak = ( '' !== $row['coa_batch'] && false !== strpos( $out, $row['coa_batch'] ) )
			|| ( '' !== $row['coa_purity'] && false !== strpos( $out, $row['coa_purity'] . ' %' ) )
			|| ( '' !== $row['coa_test_date'] && false !== strpos( $out, $row['coa_test_date'] ) )
			|| false !== strpos( $out, '<table' ) || false !== strpos( $out, '.pdf' );
		if ( false === strpos( $out, 'COA pending' ) || $leak ) {
			$draft_ok   = false;
			$problems[] = $row['SKU'];
		}
	} else {
		$want = array( $row['coa_batch'], $row['coa_test_date'], $row['coa_purity'] . ' %', $row['coa_size_mg'] . ' mg', 'href="https://example-store.test/wp-content/uploads/coa/' . $row['coa_pdf'] . '"' );
		foreach ( $want as $w ) {
			if ( false === strpos( $out, $w ) ) {
				$pub_ok     = false;
				$problems[] = $row['SKU'] . " missing $w";
			}
		}
		if ( false !== strpos( $out, 'COA pending' ) ) {
			$pub_ok     = false;
			$problems[] = $row['SKU'] . ' shows pending';
		}
	}
}
check( $draft_ok && $drafts > 0, "every draft's tab shows \"COA pending\" and no COA values ($drafts drafts)", implode( ', ', $problems ) );
check( $pub_ok, "every published product's tab shows batch, test date, purity, size and the PDF link", implode( ', ', $problems ) );

// ---------------------------------------------------------------- 5. broken rows are rejected
$good = null;
foreach ( $csv as $row ) {
	if ( 'publish' === $row['Status'] ) {
		$good = $row;
		break;
	}
}
$before = $GLOBALS['pcoa_meta'];
$cases  = array(
	'bad batch' => array( array( 'coa_batch' => 'PP-26X7-1' ), 'coa_batch' ),
	'bad date'  => array( array( 'coa_test_date' => '2026-02-30' ), 'coa_test_date' ),
	'bad date format' => array( array( 'coa_test_date' => '07/15/2026' ), 'coa_test_date' ),
	'wrong URL' => array( array( 'coa_url' => 'https://evil.test/coa/' . strtolower( $good['SKU'] ) . '/' ), 'coa_url' ),
	'bad status' => array( array( 'Status' => 'pending' ), 'Status' ),
	'bad reason' => array( array( 'status_reason' => 'looks fine' ), 'status_reason' ),
	'bad price' => array( array( 'Regular price' => '49' ), 'Regular price' ),
);
foreach ( $cases as $label => $case ) {
	$row = array_merge( $good, $case[0] );
	$e   = $importer->validate_row( $row );
	$hit = false;
	foreach ( $e as $msg ) {
		if ( 0 === strpos( $msg, $case[1] ) ) {
			$hit = true;
		}
	}
	check( $hit, "validator rejects $label ({$case[1]})", json_encode( $e ) );
}
// the deliberately broken row (bad batch, bad date, wrong URL) goes through the real file import
$broken = array_merge( $good, array( 'coa_batch' => 'PP-2613-07', 'coa_test_date' => '2026-13-45', 'coa_url' => 'https://example-store.test/coa/wrong/' ) );
$tmp    = tempnam( sys_get_temp_dir(), 'pcoa' );
$fh     = fopen( $tmp, 'w' );
fputcsv( $fh, Peptide_COA_Importer::COLUMNS, ',', '"', '' );
fputcsv( $fh, array_values( $broken ), ',', '"', '' );
fclose( $fh );
$r = $importer->import_file( $tmp );
unlink( $tmp );
$msgs = $r['errors'][2] ?? array();
$cols = array_map(
	function ( $m ) {
		return strtok( $m, ':' );
	},
	$msgs
);
check( 0 === $r['imported'] && isset( $r['errors'][2] ), 'broken row is reported, not imported', json_encode( $r ) );
check( in_array( 'coa_batch', $cols, true ) && in_array( 'coa_test_date', $cols, true ) && in_array( 'coa_url', $cols, true ),
	'broken row report names batch, date and URL', json_encode( $msgs ) );
check( $before === $GLOBALS['pcoa_meta'], 'rejected row left the stored product meta unchanged' );

echo "\n$pass passed, $fail failed\n";
exit( $fail ? 1 : 0 );
