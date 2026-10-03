<?php
/**
 * Front-end display: "Certificate of Analysis" product tab and [coa_library] shortcode.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class Peptide_COA_Display {

	/** woocommerce_product_tabs filter. */
	public static function add_product_tab( $tabs ) {
		$tabs['peptide_coa'] = array(
			'title'    => __( 'Certificate of Analysis', 'peptide-coa' ),
			'priority' => 25,
			'callback' => array( __CLASS__, 'render_tab' ),
		);
		return $tabs;
	}

	/** Tab callback: echoes the tab body for the current global $product. */
	public static function render_tab() {
		global $product;
		echo self::tab_html( $product ); // phpcs:ignore WordPress.Security.EscapeOutput -- escaped in tab_html.
	}

	/** COA values are only shown for a published product whose status reason is "ok". */
	public static function is_verified( $product ) {
		if ( ! $product ) {
			return false;
		}
		$id = $product->get_id();
		return 'publish' === $product->get_status() && 'ok' === get_post_meta( $id, '_coa_status_reason', true );
	}

	public static function tab_html( $product ) {
		$out = '<h2>' . esc_html__( 'Certificate of Analysis', 'peptide-coa' ) . '</h2>';
		if ( ! self::is_verified( $product ) ) {
			return $out . '<p class="coa-pending">' . esc_html__( 'COA pending', 'peptide-coa' ) . '</p>';
		}
		$id   = $product->get_id();
		$meta = self::meta( $id );
		$out .= '<table class="shop_attributes coa-table"><tbody>';
		$out .= self::tr( __( 'Batch', 'peptide-coa' ), esc_html( $meta['batch'] ) );
		$out .= self::tr( __( 'Test date', 'peptide-coa' ), esc_html( $meta['test_date'] ) );
		$out .= self::tr( __( 'Purity (HPLC)', 'peptide-coa' ), esc_html( $meta['purity'] ) . ' %' );
		$out .= self::tr( __( 'Declared amount', 'peptide-coa' ), esc_html( $meta['size_mg'] ) . ' mg' );
		$out .= '</tbody></table>';
		$out .= '<p><a class="coa-pdf" href="' . esc_url( peptide_coa_pdf_base() . rawurlencode( $meta['pdf'] ) ) . '" target="_blank" rel="noopener">'
			. esc_html__( 'Download the COA (PDF)', 'peptide-coa' ) . '</a>';
		if ( $meta['url'] ) {
			$out .= ' · <a class="coa-page" href="' . esc_url( $meta['url'] ) . '">' . esc_html__( 'COA page', 'peptide-coa' ) . '</a>';
		}
		return $out . '</p>';
	}

	private static function tr( $label, $value_html ) {
		return '<tr><th>' . esc_html( $label ) . '</th><td>' . $value_html . '</td></tr>';
	}

	private static function meta( $id ) {
		return array(
			'batch'     => (string) get_post_meta( $id, '_coa_batch', true ),
			'test_date' => (string) get_post_meta( $id, '_coa_test_date', true ),
			'purity'    => (string) get_post_meta( $id, '_coa_purity', true ),
			'size_mg'   => (string) get_post_meta( $id, '_coa_size_mg', true ),
			'pdf'       => (string) get_post_meta( $id, '_coa_pdf', true ),
			'url'       => (string) get_post_meta( $id, '_coa_url', true ),
		);
	}

	/**
	 * Published, verified products in library order: newest test date first, ties by SKU (rules.md 12).
	 *
	 * @return array<int, array> rows with sku, name and the COA meta.
	 */
	public static function library_rows() {
		$products = wc_get_products( array( 'status' => 'publish', 'limit' => -1 ) );
		$rows     = array();
		foreach ( $products as $product ) {
			if ( ! self::is_verified( $product ) ) {
				continue;
			}
			$rows[] = array( 'sku' => $product->get_sku(), 'name' => $product->get_name() ) + self::meta( $product->get_id() );
		}
		usort(
			$rows,
			function ( $a, $b ) {
				$c = strcmp( $b['test_date'], $a['test_date'] );
				return 0 !== $c ? $c : strcmp( $a['sku'], $b['sku'] );
			}
		);
		return $rows;
	}

	/** Teaser numbers: count and mean purity (2 decimals) of the published products. */
	public static function teaser( array $rows ) {
		$n    = count( $rows );
		$mean = $n ? round( array_sum( array_map( 'floatval', array_column( $rows, 'purity' ) ) ) / $n + 1e-12, 2 ) : 0.0;
		return array(
			'count' => $n,
			'mean'  => $mean,
			'text'  => sprintf( '%d verified COAs · average purity %s %%', $n, number_format( $mean, 2, '.', '' ) ),
		);
	}

	/** [coa_library] shortcode. */
	public static function library_shortcode( $atts = array() ) {
		$rows   = self::library_rows();
		$teaser = self::teaser( $rows );
		$base   = peptide_coa_pdf_base();
		$out    = '<div class="coa-library">';
		$out   .= '<p class="coa-teaser" data-count="' . esc_attr( $teaser['count'] ) . '" data-mean="' . esc_attr( number_format( $teaser['mean'], 2, '.', '' ) ) . '">'
			. esc_html( $teaser['text'] ) . '</p>';
		$out   .= '<table class="coa-library-table"><thead><tr><th>' . esc_html__( 'Product', 'peptide-coa' ) . '</th><th>'
			. esc_html__( 'Batch', 'peptide-coa' ) . '</th><th>' . esc_html__( 'Test date', 'peptide-coa' ) . '</th><th>'
			. esc_html__( 'Purity', 'peptide-coa' ) . '</th><th>' . esc_html__( 'COA', 'peptide-coa' ) . '</th></tr></thead><tbody>';
		foreach ( $rows as $r ) {
			$out .= '<tr data-sku="' . esc_attr( $r['sku'] ) . '"><td>' . esc_html( $r['name'] ) . '</td><td>' . esc_html( $r['batch'] )
				. '</td><td>' . esc_html( $r['test_date'] ) . '</td><td>' . esc_html( $r['purity'] ) . ' %</td><td><a href="'
				. esc_url( $base . rawurlencode( $r['pdf'] ) ) . '">' . esc_html( $r['pdf'] ) . '</a></td></tr>';
		}
		return $out . '</tbody></table></div>';
	}
}
