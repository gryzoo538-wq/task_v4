<?php
/**
 * Reads woocommerce_import.csv, validates every row against the store rules
 * and stores the COA columns as product meta. Invalid rows are reported and
 * not imported.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class Peptide_COA_Importer {

	const URL_BASE = 'https://example-store.test/coa/';

	const COLUMNS = array( 'SKU', 'Name', 'Regular price', 'Status', 'coa_batch', 'coa_test_date', 'coa_purity', 'coa_size_mg', 'coa_pdf', 'coa_url', 'status_reason' );

	const REASONS = array( 'ok', 'no COA', 'conflicting COAs', 'missing field', 'size conflict', 'purity below 98.0', 'identity failed', 'COA older than 12 months' );

	const STATUSES = array( 'publish', 'draft' );

	/** CSV column => product meta key. */
	const META = array(
		'coa_batch'     => '_coa_batch',
		'coa_test_date' => '_coa_test_date',
		'coa_purity'    => '_coa_purity',
		'coa_size_mg'   => '_coa_size_mg',
		'coa_pdf'       => '_coa_pdf',
		'coa_url'       => '_coa_url',
		'status_reason' => '_coa_status_reason',
	);

	/**
	 * Parse a CSV file into associative rows keyed by header.
	 *
	 * @return array{rows: array<int, array>, errors: array<int, string[]>} rows keyed by file line number.
	 */
	public function read_file( $path ) {
		$rows   = array();
		$errors = array();
		$fh     = fopen( $path, 'r' );
		if ( ! $fh ) {
			return array( 'rows' => array(), 'errors' => array( 0 => array( 'cannot open file' ) ) );
		}
		$header = fgetcsv( $fh, 0, ',', '"', '' );
		if ( is_array( $header ) && isset( $header[0] ) ) {
			$header[0] = preg_replace( '/^\xEF\xBB\xBF/', '', $header[0] );
		}
		if ( self::COLUMNS !== $header ) {
			fclose( $fh );
			return array( 'rows' => array(), 'errors' => array( 1 => array( 'header must be: ' . implode( ',', self::COLUMNS ) ) ) );
		}
		$line = 1;
		while ( ( $cells = fgetcsv( $fh, 0, ',', '"', '' ) ) !== false ) {
			$line++;
			if ( array( null ) === $cells ) {
				continue;
			}
			if ( count( $cells ) !== count( self::COLUMNS ) ) {
				$errors[ $line ] = array( 'expected ' . count( self::COLUMNS ) . ' columns, got ' . count( $cells ) );
				continue;
			}
			$rows[ $line ] = array_combine( self::COLUMNS, array_map( 'trim', $cells ) );
		}
		fclose( $fh );
		return array( 'rows' => $rows, 'errors' => $errors );
	}

	/**
	 * Validate one row. Returns a list of error strings (empty when valid).
	 */
	public function validate_row( array $row ) {
		$e = array();
		foreach ( self::COLUMNS as $col ) {
			if ( ! array_key_exists( $col, $row ) ) {
				$e[] = "missing column $col";
			}
		}
		if ( $e ) {
			return $e;
		}
		if ( ! preg_match( '/^[A-Z0-9][A-Z0-9_-]*$/', $row['SKU'] ) ) {
			$e[] = 'SKU: invalid "' . $row['SKU'] . '"';
		}
		if ( '' === $row['Name'] ) {
			$e[] = 'Name: empty';
		}
		if ( ! preg_match( '/^\d+\.\d{2}$/', $row['Regular price'] ) || (float) $row['Regular price'] <= 0 ) {
			$e[] = 'Regular price: must be a positive amount with 2 decimals, got "' . $row['Regular price'] . '"';
		}
		if ( ! in_array( $row['Status'], self::STATUSES, true ) ) {
			$e[] = 'Status: must be publish or draft, got "' . $row['Status'] . '"';
		}
		if ( ! in_array( $row['status_reason'], self::REASONS, true ) ) {
			$e[] = 'status_reason: not an allowed value, got "' . $row['status_reason'] . '"';
		}
		$batch = $row['coa_batch'];
		if ( '' !== $batch && ! self::valid_batch( $batch ) ) {
			$e[] = 'coa_batch: must match PP-YYMM-NNN, got "' . $batch . '"';
		}
		if ( '' !== $row['coa_test_date'] && ! self::valid_date( $row['coa_test_date'] ) ) {
			$e[] = 'coa_test_date: must be a real date YYYY-MM-DD, got "' . $row['coa_test_date'] . '"';
		}
		if ( '' !== $row['coa_purity'] && ( ! preg_match( '/^\d{1,3}\.\d$/', $row['coa_purity'] ) || (float) $row['coa_purity'] > 100 ) ) {
			$e[] = 'coa_purity: must be a percentage with 1 decimal, got "' . $row['coa_purity'] . '"';
		}
		if ( '' !== $row['coa_size_mg'] && ! preg_match( '/^[1-9]\d*$/', $row['coa_size_mg'] ) ) {
			$e[] = 'coa_size_mg: must be whole mg, got "' . $row['coa_size_mg'] . '"';
		}
		if ( '' !== $row['coa_pdf'] && ! preg_match( '/^[A-Za-z0-9][A-Za-z0-9._-]*\.pdf$/', $row['coa_pdf'] ) ) {
			$e[] = 'coa_pdf: must be a PDF file name, got "' . $row['coa_pdf'] . '"';
		}
		// URL rule (rules.md 11): set whenever the batch is known, blank otherwise.
		$expected = '' === $batch ? '' : self::URL_BASE . strtolower( $row['SKU'] ) . '-' . strtolower( $batch ) . '/';
		if ( $row['coa_url'] !== $expected ) {
			$e[] = 'coa_url: expected "' . $expected . '", got "' . $row['coa_url'] . '"';
		}
		// Status / reason consistency (rules.md 9-10).
		if ( 'publish' === $row['Status'] ) {
			if ( 'ok' !== $row['status_reason'] ) {
				$e[] = 'status_reason: published products must have reason "ok"';
			}
			foreach ( array( 'coa_batch', 'coa_test_date', 'coa_purity', 'coa_size_mg', 'coa_pdf', 'coa_url' ) as $c ) {
				if ( '' === $row[ $c ] ) {
					$e[] = "$c: required for a published product";
				}
			}
			if ( '' !== $row['coa_purity'] && (float) $row['coa_purity'] < 98.0 ) {
				$e[] = 'coa_purity: published products need 98.0 % or higher';
			}
		} elseif ( 'draft' === $row['Status'] ) {
			if ( 'ok' === $row['status_reason'] ) {
				$e[] = 'status_reason: drafts need a hold reason, not "ok"';
			}
			if ( 'no COA' === $row['status_reason'] ) {
				foreach ( array_keys( self::META ) as $c ) {
					if ( 'status_reason' !== $c && '' !== $row[ $c ] ) {
						$e[] = "$c: must be blank when there is no COA";
					}
				}
			}
			if ( 'conflicting COAs' === $row['status_reason'] ) {
				foreach ( array( 'coa_test_date', 'coa_purity', 'coa_size_mg', 'coa_pdf' ) as $c ) {
					if ( '' !== $row[ $c ] ) {
						$e[] = "$c: must be blank for conflicting COAs";
					}
				}
			}
		}
		return $e;
	}

	public static function valid_batch( $batch ) {
		if ( ! preg_match( '/^PP-(\d{2})(\d{2})-(\d{3})$/', $batch, $m ) ) {
			return false;
		}
		$month = (int) $m[2];
		return $month >= 1 && $month <= 12;
	}

	public static function valid_date( $date ) {
		if ( ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})$/', $date, $m ) ) {
			return false;
		}
		return checkdate( (int) $m[2], (int) $m[3], (int) $m[1] );
	}

	/**
	 * Validate the whole file, then import the valid rows.
	 *
	 * @return array{imported:int, errors: array<int, string[]>, skus: string[]}
	 */
	public function import_file( $path ) {
		$parsed = $this->read_file( $path );
		return $this->import_rows( $parsed['rows'], $parsed['errors'] );
	}

	public function import_rows( array $rows, array $errors = array() ) {
		$imported = 0;
		$skus     = array();
		$seen     = array();
		foreach ( $rows as $line => $row ) {
			$row_errors = $this->validate_row( $row );
			if ( ! $row_errors && isset( $seen[ $row['SKU'] ] ) ) {
				$row_errors[] = 'SKU: duplicate of line ' . $seen[ $row['SKU'] ];
			}
			if ( $row_errors ) {
				$errors[ $line ] = $row_errors;
				continue;
			}
			$seen[ $row['SKU'] ] = $line;
			$this->save_row( $row );
			$imported++;
			$skus[] = $row['SKU'];
		}
		ksort( $errors );
		return array( 'imported' => $imported, 'errors' => $errors, 'skus' => $skus );
	}

	/** Create or update the WooCommerce product for one valid row. */
	protected function save_row( array $row ) {
		$id      = wc_get_product_id_by_sku( $row['SKU'] );
		$product = $id ? wc_get_product( $id ) : new WC_Product_Simple();
		if ( ! $id ) {
			$product->set_sku( $row['SKU'] );
		}
		$product->set_name( $row['Name'] );
		$product->set_regular_price( $row['Regular price'] );
		$product->set_status( $row['Status'] );
		$id = $product->save();
		foreach ( self::META as $col => $key ) {
			if ( '' === $row[ $col ] ) {
				delete_post_meta( $id, $key );
			} else {
				update_post_meta( $id, $key, $row[ $col ] );
			}
		}
		return $id;
	}
}
