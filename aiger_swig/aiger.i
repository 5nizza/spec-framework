%module aiger_wrap

%{
#define SWIG_FILE_WITH_INIT
#include "aiger.h"
static int index_err = 0;
%}

%include "typemaps.i"
%include "exception.i"
%include <cstring.i>
%cstring_output_maxsize(char *str, size_t len);

%typemap(in) unsigned int *
{
  int len = PySequence_Length($input);
  $1 = malloc(len * sizeof(unsigned));
  int i;
  for(i = 0; i < len; i++)
  {
    PyObject *o = PySequence_GetItem($input,i);
    if (PyInt_Check(o))
      $1[i] = (unsigned) PyInt_AsLong(o);
    else
    {
      free($1);
      PyErr_SetString(PyExc_ValueError,"Sequence elements must be numbers");      
      return NULL;
    }
    // printf("%d\n", _tmp[i]);
  }
}
%typemap(freearg) unsigned int *
{
  free($1);
}

%feature("autodoc", "1");


%include "aiger.h"



/* added functionality to aiger.h */
void
aiger_redefine_input_as_and (aiger* public, unsigned input_lit, unsigned rhs0, unsigned rhs1);  /* TODO: better error handling (index out of arrays) */

/* We define exception handler, 
   and all the functions that follow the handler until reaching `%exception`
   are wrapped by this handler.
*/
%exception {
  assert(!index_err);
  $action
  if (index_err) {
    index_err = 0; // clear flag for next time
    PyErr_SetString(PyExc_IndexError, "Index is out of array");
    return NULL;
  }
}

%inline %{

/*
aiger_symbol* get_ith_input(aiger* public, unsigned i) {
    return public->inputs + i;
}
*/

aiger_symbol* get_ith_latch(aiger* public, unsigned i) {
  if (i < public->num_latches)
    return public->latches + i;
  
  index_err = 1;
  return NULL;
}

aiger_symbol* get_ith_fairness(aiger* public, unsigned i) {
  if (i < public->num_fairness)
    return public->fairness + i;
  
  index_err = 1;
  return NULL;
}

int get_justice_lit(aiger* public, int justice_index, int lit_index) {
  if (justice_index < public->num_justice && 
      lit_index < public->justice[justice_index].size)
    return public->justice[justice_index].lits[lit_index];

  index_err = 1;
  return 0;
}


void set_justice_lit(aiger* public, 
                     int justice_index, 
                     int lit_index, 
                     int new_lit_value) {
  if (justice_index < public->num_justice && 
      lit_index < public->justice[justice_index].size)
    public->justice[justice_index].lits[lit_index] = new_lit_value;
  else
    index_err = 1;
}

%}

%exception;  /* end of exception wrapping */




