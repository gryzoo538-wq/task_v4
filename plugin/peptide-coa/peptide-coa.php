<?php
/**
 * Plugin Name:       Peptide COA
 * Plugin URI:        https://example-store.test/
 * Description:       Imports Certificate of Analysis (COA) data from woocommerce_import.csv into WooCommerce products and displays it in a product tab and a [coa_library] shortcode.
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            Example Store web team
 * License:           GPL-2.0-or-later
 * Text Domain:       peptide-coa
 * WC requires at least: 7.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'PEPTIDE_COA_VERSION', '1.0.0' );
define( 'PEPTIDE_COA_DIR', plugin_dir_path( __FILE__ ) );

require_once PEPTIDE_COA_DIR . 'includes/class-coa-importer.php';
require_once PEPTIDE_COA_DIR . 'includes/class-coa-display.php';

/**
 * Base URL under which the COA PDF files (coa_pdf column) are served.
 * Defaults to wp-content/uploads/coa/; override with the peptide_coa_pdf_base option or filter.
 */
function peptide_coa_pdf_base() {
	$base = get_option( 'peptide_coa_pdf_base', '' );
	if ( '' === $base ) {
		$base = content_url( '/uploads/coa/' );
	}
	return apply_filters( 'peptide_coa_pdf_base', trailingslashit( $base ) );
}

add_filter( 'woocommerce_product_tabs', array( 'Peptide_COA_Display', 'add_product_tab' ) );
add_shortcode( 'coa_library', array( 'Peptide_COA_Display', 'library_shortcode' ) );

// Admin screen: Tools > Peptide COA import.
add_action( 'admin_menu', 'peptide_coa_admin_menu' );

function peptide_coa_admin_menu() {
	add_management_page( 'Peptide COA import', 'Peptide COA import', 'manage_woocommerce', 'peptide-coa-import', 'peptide_coa_admin_page' );
}

function peptide_coa_admin_page() {
	if ( ! current_user_can( 'manage_woocommerce' ) ) {
		return;
	}
	echo '<div class="wrap"><h1>Peptide COA import</h1>';
	if ( isset( $_POST['peptide_coa_import'] ) && check_admin_referer( 'peptide_coa_import' ) && ! empty( $_FILES['coa_csv']['tmp_name'] ) ) {
		$importer = new Peptide_COA_Importer();
		$result   = $importer->import_file( $_FILES['coa_csv']['tmp_name'] );
		printf( '<p>%d rows imported, %d rows rejected.</p>', (int) $result['imported'], count( $result['errors'] ) );
		if ( $result['errors'] ) {
			echo '<ul>';
			foreach ( $result['errors'] as $line => $errs ) {
				printf( '<li>Line %d: %s</li>', (int) $line, esc_html( implode( '; ', $errs ) ) );
			}
			echo '</ul>';
		}
	}
	echo '<form method="post" enctype="multipart/form-data">';
	wp_nonce_field( 'peptide_coa_import' );
	echo '<input type="file" name="coa_csv" accept=".csv" required> ';
	echo '<button class="button button-primary" name="peptide_coa_import" value="1">Import woocommerce_import.csv</button>';
	echo '</form></div>';
}

// WP-CLI: wp peptide-coa import <file>
if ( defined( 'WP_CLI' ) && WP_CLI ) {
	WP_CLI::add_command(
		'peptide-coa import',
		function ( $args ) {
			$importer = new Peptide_COA_Importer();
			$result   = $importer->import_file( $args[0] );
			foreach ( $result['errors'] as $line => $errs ) {
				WP_CLI::warning( "Line $line: " . implode( '; ', $errs ) );
			}
			WP_CLI::success( $result['imported'] . ' rows imported, ' . count( $result['errors'] ) . ' rejected.' );
		}
	);
}
