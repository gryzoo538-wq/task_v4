<?php
/**
 * Minimal in-memory stand-ins for the WordPress / WooCommerce functions the
 * plugin uses, so the tests run with plain `php` and no WordPress install.
 */

define( 'ABSPATH', __DIR__ . '/' );

$GLOBALS['pcoa_filters']    = array();
$GLOBALS['pcoa_shortcodes'] = array();
$GLOBALS['pcoa_posts']      = array(); // id => WC_Product_Simple
$GLOBALS['pcoa_meta']       = array(); // id => [key => value]
$GLOBALS['pcoa_next_id']    = 100;
$GLOBALS['pcoa_options']    = array();

function plugin_dir_path( $file ) {
	return rtrim( dirname( $file ), '/' ) . '/';
}
function content_url( $path = '' ) {
	return 'https://example-store.test/wp-content' . $path;
}
function trailingslashit( $s ) {
	return rtrim( $s, '/\\' ) . '/';
}
function get_option( $name, $default = false ) {
	return array_key_exists( $name, $GLOBALS['pcoa_options'] ) ? $GLOBALS['pcoa_options'][ $name ] : $default;
}
function add_filter( $hook, $cb, $priority = 10, $args = 1 ) {
	$GLOBALS['pcoa_filters'][ $hook ][] = $cb;
	return true;
}
function add_action( $hook, $cb, $priority = 10, $args = 1 ) {
	return add_filter( $hook, $cb, $priority, $args );
}
function apply_filters( $hook, $value, ...$rest ) {
	foreach ( $GLOBALS['pcoa_filters'][ $hook ] ?? array() as $cb ) {
		$value = call_user_func( $cb, $value, ...$rest );
	}
	return $value;
}
function add_shortcode( $tag, $cb ) {
	$GLOBALS['pcoa_shortcodes'][ $tag ] = $cb;
}
function do_shortcode( $content ) {
	return preg_replace_callback(
		'/\[(\w+)\]/',
		function ( $m ) {
			return isset( $GLOBALS['pcoa_shortcodes'][ $m[1] ] ) ? call_user_func( $GLOBALS['pcoa_shortcodes'][ $m[1] ], array() ) : $m[0];
		},
		$content
	);
}
function __( $s, $domain = null ) {
	return $s;
}
function esc_html__( $s, $domain = null ) {
	return esc_html( $s );
}
function esc_html( $s ) {
	return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' );
}
function esc_attr( $s ) {
	return htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' );
}
function esc_url( $s ) {
	return preg_match( '#^https?://#', (string) $s ) ? htmlspecialchars( (string) $s, ENT_QUOTES, 'UTF-8' ) : '';
}
function get_post_meta( $id, $key, $single = false ) {
	$v = $GLOBALS['pcoa_meta'][ $id ][ $key ] ?? '';
	return $single ? $v : ( '' === $v ? array() : array( $v ) );
}
function update_post_meta( $id, $key, $value ) {
	$GLOBALS['pcoa_meta'][ $id ][ $key ] = $value;
	return true;
}
function delete_post_meta( $id, $key ) {
	unset( $GLOBALS['pcoa_meta'][ $id ][ $key ] );
	return true;
}

class WC_Product_Simple {
	private $data = array( 'id' => 0, 'sku' => '', 'name' => '', 'regular_price' => '', 'status' => 'draft' );
	public function get_id() { return $this->data['id']; }
	public function get_sku() { return $this->data['sku']; }
	public function get_name() { return $this->data['name']; }
	public function get_regular_price() { return $this->data['regular_price']; }
	public function get_status() { return $this->data['status']; }
	public function set_sku( $v ) { $this->data['sku'] = $v; }
	public function set_name( $v ) { $this->data['name'] = $v; }
	public function set_regular_price( $v ) { $this->data['regular_price'] = $v; }
	public function set_status( $v ) { $this->data['status'] = $v; }
	public function save() {
		if ( ! $this->data['id'] ) {
			$this->data['id'] = $GLOBALS['pcoa_next_id']++;
		}
		$GLOBALS['pcoa_posts'][ $this->data['id'] ] = clone $this;
		return $this->data['id'];
	}
}
function wc_get_product_id_by_sku( $sku ) {
	foreach ( $GLOBALS['pcoa_posts'] as $id => $p ) {
		if ( $p->get_sku() === $sku ) {
			return $id;
		}
	}
	return 0;
}
function wc_get_product( $id ) {
	return isset( $GLOBALS['pcoa_posts'][ $id ] ) ? clone $GLOBALS['pcoa_posts'][ $id ] : false;
}
function wc_get_products( $args ) {
	$out = array();
	foreach ( $GLOBALS['pcoa_posts'] as $p ) {
		if ( isset( $args['status'] ) && $p->get_status() !== $args['status'] ) {
			continue;
		}
		$out[] = clone $p;
	}
	return $out;
}
function pcoa_reset_store() {
	$GLOBALS['pcoa_posts']   = array();
	$GLOBALS['pcoa_meta']    = array();
	$GLOBALS['pcoa_next_id'] = 100;
}
